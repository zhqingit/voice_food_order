import Flutter
import AVFoundation

/// Single-AVAudioEngine bridge for simultaneous recording (16kHz PCM16 mono)
/// and playback (24kHz PCM16 mono).  Does NOT manage AVAudioSession — the Dart
/// side must configure it (via the audio_session package) before calling
/// startSession.
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
        // We connect the player node to the main mixer using Float32 at the
        // playback sample rate.  feedAudio() converts incoming Int16 → Float32
        // before scheduling buffers.
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

        // --- Recording tap ---
        let inputNode = engine.inputNode
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

        inputNode.installTap(onBus: 0, bufferSize: 4096, format: hwFormat) {
            [weak self] buffer, _ in
            guard self != nil, let sink = sink else { return }

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

            // Copy Int16 samples to Data.
            let byteCount = Int(converted.frameLength) * 2  // 16-bit = 2 bytes
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
            result(true)  // silently ignore if not running
            return
        }

        let bytes = typedData.data
        let sampleCount = bytes.count / 2  // 16-bit samples
        guard sampleCount > 0 else {
            result(true)
            return
        }

        // Create a Float32 buffer at the playback sample rate.
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

        // Convert Int16 → Float32.
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

        playerNode.scheduleBuffer(buffer)
        result(true)
    }

    private func clearPlayback(result: @escaping FlutterResult) {
        guard let playerNode = playerNode else {
            result(true)
            return
        }
        // stop() flushes all scheduled buffers; play() re-arms the node.
        playerNode.stop()
        playerNode.play()
        result(true)
    }

    private func stopSession(result: @escaping FlutterResult) {
        tearDown()
        result(true)
    }

    private func tearDown() {
        if let engine = engine {
            engine.inputNode.removeTap(onBus: 0)
            playerNode?.stop()
            engine.stop()
        }
        playerNode = nil
        engine = nil
    }
}
