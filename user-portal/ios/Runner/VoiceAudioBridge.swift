import Flutter
import AVFoundation

/// Single-AVAudioEngine bridge for simultaneous recording (16kHz PCM16 mono)
/// and playback (24kHz PCM16 mono).  Does NOT manage AVAudioSession — the Dart
/// side must configure it (via the audio_session package) before calling
/// startSession.
///
/// Echo prevention uses two layers:
///   1. Hardware AEC via `setVoiceProcessingEnabled(true)` on the input node
///      (switches the I/O unit from RemoteIO to VoiceProcessingIO).
///   2. Mic muting during playback using AVAudioPlayerNode completion callbacks
///      as a safety net in case AEC alone is insufficient at high volume.
class VoiceAudioBridge: NSObject, FlutterStreamHandler {

    // MARK: – Flutter channels
    private let methodChannel: FlutterMethodChannel
    private let eventChannel: FlutterEventChannel
    private var eventSink: FlutterEventSink?

    // MARK: – Audio engine
    private var engine: AVAudioEngine?
    private var playerNode: AVAudioPlayerNode?

    // Desired output formats (actual hardware rate may differ; we convert).
    private let recordSampleRate: Double = 16000
    private let playbackSampleRate: Double = 24000

    // MARK: – Mic muting state
    /// Number of playback buffers currently scheduled / playing.
    /// When > 0 the mic tap drops audio. Accessed from multiple threads.
    private let pendingBuffers = AtomicCounter()
    /// True while the mic should be muted (bot is speaking).
    private var micMuted: Bool { pendingBuffers.value > 0 }

    // MARK: – Init

    init(messenger: FlutterBinaryMessenger) {
        methodChannel = FlutterMethodChannel(
            name: "com.restoai.voice/audio_bridge",
            binaryMessenger: messenger)
        eventChannel = FlutterEventChannel(
            name: "com.restoai.voice/audio_bridge/recorded",
            binaryMessenger: messenger)
        super.init()
        methodChannel.setMethodCallHandler(handle)
        eventChannel.setStreamHandler(self)
    }

    // MARK: – FlutterStreamHandler

    func onListen(withArguments arguments: Any?,
                  eventSink events: @escaping FlutterEventSink) -> FlutterError? {
        eventSink = events
        return nil
    }

    func onCancel(withArguments arguments: Any?) -> FlutterError? {
        eventSink = nil
        return nil
    }

    // MARK: – Method dispatch

    private func handle(_ call: FlutterMethodCall, result: @escaping FlutterResult) {
        switch call.method {
        case "startSession":
            startSession(result: result)
        case "feedAudio":
            if let data = call.arguments as? FlutterStandardTypedData {
                feedAudio(data, result: result)
            } else {
                result(FlutterError(code: "INVALID_ARG",
                                    message: "Expected Uint8List", details: nil))
            }
        case "clearPlayback":
            clearPlayback(result: result)
        case "stopSession":
            stopSession(result: result)
        default:
            result(FlutterMethodNotImplemented)
        }
    }

    // MARK: – Core methods

    private func startSession(result: @escaping FlutterResult) {
        // Tear down any previous session.
        tearDown()

        let engine = AVAudioEngine()
        let playerNode = AVAudioPlayerNode()

        // --- Playback graph ---
        guard let playerFormat = AVAudioFormat(
            commonFormat: .pcmFormatFloat32,
            sampleRate: playbackSampleRate,
            channels: 1,
            interleaved: false) else {
            result(FlutterError(code: "FORMAT",
                                message: "Cannot create player format", details: nil))
            return
        }

        engine.attach(playerNode)
        engine.connect(playerNode, to: engine.mainMixerNode, format: playerFormat)

        // --- Recording setup ---
        let inputNode = engine.inputNode

        // Enable hardware echo cancellation (AEC) + automatic gain control.
        // This switches the I/O unit from RemoteIO to VoiceProcessingIO.
        // Must be done BEFORE reading inputFormat because it changes the
        // hardware format.
        if #available(iOS 13.0, *) {
            do {
                try inputNode.setVoiceProcessingEnabled(true)
                inputNode.isVoiceProcessingAGCEnabled = true
            } catch {
                // Non-fatal — continue without hardware AEC.
                // Mic muting (layer 2) will still prevent echo.
            }
        }

        let hwFormat = inputNode.outputFormat(forBus: 0)

        guard hwFormat.sampleRate > 0 else {
            result(FlutterError(code: "NO_INPUT",
                                message: "No audio input available", details: nil))
            return
        }

        guard let recordFormat = AVAudioFormat(
            commonFormat: .pcmFormatInt16,
            sampleRate: recordSampleRate,
            channels: 1,
            interleaved: true) else {
            result(FlutterError(code: "FORMAT",
                                message: "Cannot create record format", details: nil))
            return
        }

        guard let converter = AVAudioConverter(from: hwFormat, to: recordFormat) else {
            result(FlutterError(code: "CONVERTER",
                                message: "Cannot create sample-rate converter", details: nil))
            return
        }

        let ratio = hwFormat.sampleRate / recordSampleRate
        let sink = eventSink  // capture for closure
        let pending = pendingBuffers  // capture for closure

        inputNode.installTap(onBus: 0, bufferSize: 4096, format: hwFormat) {
            [weak self] buffer, _ in
            guard self != nil, let sink = sink else { return }

            // Layer 2: drop mic audio while bot is speaking.
            if pending.value > 0 { return }

            let frameCapacity = AVAudioFrameCount(Double(buffer.frameLength) / ratio)
            guard frameCapacity > 0,
                  let converted = AVAudioPCMBuffer(pcmFormat: recordFormat,
                                                    frameCapacity: frameCapacity) else { return }

            var error: NSError?
            let inputBlock: AVAudioConverterInputBlock = { _, outStatus in
                outStatus.pointee = .haveData
                return buffer
            }
            converter.convert(to: converted, error: &error, withInputFrom: inputBlock)
            if error != nil { return }

            let byteCount = Int(converted.frameLength) * 2
            guard let channelData = converted.int16ChannelData else { return }
            let data = Data(bytes: channelData[0], count: byteCount)

            DispatchQueue.main.async {
                sink(FlutterStandardTypedData(bytes: data))
            }
        }

        // --- Start ---
        engine.prepare()
        do {
            try engine.start()
        } catch {
            result(FlutterError(code: "ENGINE",
                                message: "AVAudioEngine start failed: \(error.localizedDescription)",
                                details: nil))
            return
        }
        playerNode.play()

        self.engine = engine
        self.playerNode = playerNode

        result(true)
    }

    private func feedAudio(_ typedData: FlutterStandardTypedData,
                           result: @escaping FlutterResult) {
        guard let playerNode = playerNode else {
            result(true)
            return
        }

        let bytes = typedData.data
        let sampleCount = bytes.count / 2
        guard sampleCount > 0 else {
            result(true)
            return
        }

        guard let format = AVAudioFormat(
            commonFormat: .pcmFormatFloat32,
            sampleRate: playbackSampleRate,
            channels: 1,
            interleaved: false),
              let buffer = AVAudioPCMBuffer(pcmFormat: format,
                                             frameCapacity: AVAudioFrameCount(sampleCount)) else {
            result(true)
            return
        }

        buffer.frameLength = AVAudioFrameCount(sampleCount)

        guard let floatData = buffer.floatChannelData else {
            result(true)
            return
        }
        bytes.withUnsafeBytes { raw in
            guard let src = raw.baseAddress?.assumingMemoryBound(to: Int16.self) else { return }
            for i in 0..<sampleCount {
                floatData[0][i] = Float(src[i]) / 32768.0
            }
        }

        // Increment pending count BEFORE scheduling so the mic tap sees it
        // immediately.  The completion fires on an internal AVAudioEngine
        // thread after the buffer has been consumed — no method channel
        // round-trip needed.
        pendingBuffers.increment()
        playerNode.scheduleBuffer(buffer, completionCallbackType: .dataPlayedBack) {
            [weak self] _ in
            self?.pendingBuffers.decrement()
        }

        result(true)
    }

    private func clearPlayback(result: @escaping FlutterResult) {
        guard let playerNode = playerNode else {
            result(true)
            return
        }
        // stop() flushes all scheduled buffers (completion callbacks fire
        // with .interrupted); play() re-arms the node.
        // Reset pending count to 0 so the mic unmutes immediately.
        pendingBuffers.reset()
        playerNode.stop()
        playerNode.play()
        result(true)
    }

    private func stopSession(result: @escaping FlutterResult) {
        tearDown()
        result(true)
    }

    private func tearDown() {
        pendingBuffers.reset()
        if let engine = engine {
            engine.inputNode.removeTap(onBus: 0)
            playerNode?.stop()
            engine.stop()
        }
        playerNode = nil
        engine = nil
    }
}

// MARK: – Thread-safe counter

/// A simple atomic counter for cross-thread access between the audio render
/// thread (input tap) and the main / AVAudioEngine callback threads.
private final class AtomicCounter {
    private var _value: Int32 = 0

    var value: Int32 {
        OSAtomicAdd32(0, &_value)
    }

    func increment() {
        OSAtomicIncrement32(&_value)
    }

    func decrement() {
        OSAtomicDecrement32(&_value)
    }

    func reset() {
        while !OSAtomicCompareAndSwap32(_value, 0, &_value) {}
    }
}
