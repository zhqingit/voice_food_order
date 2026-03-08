// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for Spanish Castilian (`es`).
class AppLocalizationsEs extends AppLocalizations {
  AppLocalizationsEs([String locale = 'es']) : super(locale);

  @override
  String get appTitle => 'Pedido';

  @override
  String get storesTitle => 'Tiendas';

  @override
  String get pickStore => '¿Qué se te antoja hoy?';

  @override
  String get storeId => 'ID de tienda';

  @override
  String get storeName => 'Nombre de tienda';

  @override
  String get openVoiceOrder => 'Pedido por voz';

  @override
  String get settingsTitle => 'Configuración';

  @override
  String get appearanceTitle => 'Apariencia';

  @override
  String get themeTitle => 'Tema';

  @override
  String get languageTitle => 'Idioma';

  @override
  String get authTitle => 'Inicia sesión para continuar';

  @override
  String get login => 'Iniciar sesión';

  @override
  String get signup => 'Registrarse';

  @override
  String get email => 'Correo';

  @override
  String get password => 'Contraseña';

  @override
  String get continueAsGuest => 'Continuar como invitado';

  @override
  String get guestModeEnabled => 'Modo invitado activado.';

  @override
  String get voiceTitle => 'Pedido por voz';

  @override
  String get listening => 'Escuchando…';

  @override
  String get connecting => 'Conectando…';

  @override
  String get tapMicToStart => 'Toca el micrófono para comenzar';

  @override
  String get whatAreYouCraving => '¿Qué se te\nantoja?';

  @override
  String get goodMorning => 'Buenos días';

  @override
  String get goodAfternoon => 'Buenas tardes';

  @override
  String get goodEvening => 'Buenas noches';

  @override
  String get searchRestaurants => 'Buscar restaurantes...';

  @override
  String get nearbyRestaurants => 'Restaurantes cercanos';

  @override
  String get somethingWentWrong => 'Algo salió mal';

  @override
  String get tryAgain => 'Reintentar';

  @override
  String get noMatchesFound => 'Sin resultados';

  @override
  String get noRestaurantsYet => 'Aún no hay restaurantes';

  @override
  String get storeOpen => 'Abierto';

  @override
  String get storeClosed => 'Cerrado';

  @override
  String get pickup => 'Recoger';

  @override
  String get delivery => 'Entrega';

  @override
  String get sessionComplete => 'Sesión completa';

  @override
  String thanksForOrdering(Object storeName) {
    return 'Gracias por ordenar en $storeName';
  }

  @override
  String get orderSummary => 'Resumen del pedido';

  @override
  String get item => 'Artículo';

  @override
  String get subtotal => 'Subtotal';

  @override
  String get tax => 'Impuesto';

  @override
  String get total => 'Total';

  @override
  String get noItemsOrdered => 'No se ordenaron artículos.';

  @override
  String get howWasExperience => '¿Cómo fue tu experiencia?';

  @override
  String get thanksForFeedback => '¡Gracias por tu opinión!';

  @override
  String get newOrder => 'Nuevo pedido';

  @override
  String get about => 'Acerca de';

  @override
  String get appName => 'Nombre de la app';

  @override
  String get appNameValue => 'Resto AI';

  @override
  String get version => 'Versión';

  @override
  String get themeSignature => 'Firma';

  @override
  String get themeLight => 'Claro';

  @override
  String get themeDark => 'Oscuro';

  @override
  String get themeOcean => 'Océano';

  @override
  String get themeSunset => 'Atardecer';

  @override
  String get themeForest => 'Bosque';

  @override
  String get themeContrast => 'Contraste';
}
