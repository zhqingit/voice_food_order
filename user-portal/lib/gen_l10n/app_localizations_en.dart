// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for English (`en`).
class AppLocalizationsEn extends AppLocalizations {
  AppLocalizationsEn([String locale = 'en']) : super(locale);

  @override
  String get appTitle => 'VoxEats';

  @override
  String get storesTitle => 'Stores';

  @override
  String get pickStore => 'What are you craving today?';

  @override
  String get storeId => 'Store ID';

  @override
  String get storeName => 'Store name';

  @override
  String get openVoiceOrder => 'Open voice order';

  @override
  String get settingsTitle => 'Settings';

  @override
  String get appearanceTitle => 'Appearance';

  @override
  String get themeTitle => 'Theme';

  @override
  String get languageTitle => 'Language';

  @override
  String get authTitle => 'Sign in to continue';

  @override
  String get login => 'Login';

  @override
  String get signup => 'Sign up';

  @override
  String get email => 'Email';

  @override
  String get password => 'Password';

  @override
  String get continueAsGuest => 'Continue as Guest';

  @override
  String get guestModeEnabled => 'Guest mode enabled.';

  @override
  String get voiceTitle => 'Voice order';

  @override
  String get listening => 'Listening…';

  @override
  String get connecting => 'Connecting…';

  @override
  String get tapMicToStart => 'Tap the mic to start';

  @override
  String get whatAreYouCraving => 'What are you\ncraving?';

  @override
  String get goodMorning => 'Good morning';

  @override
  String get goodAfternoon => 'Good afternoon';

  @override
  String get goodEvening => 'Good evening';

  @override
  String get searchRestaurants => 'Search restaurants...';

  @override
  String get nearbyRestaurants => 'Nearby Restaurants';

  @override
  String get somethingWentWrong => 'Something went wrong';

  @override
  String get tryAgain => 'Try Again';

  @override
  String get noMatchesFound => 'No matches found';

  @override
  String get noRestaurantsYet => 'No restaurants yet';

  @override
  String get storeUnavailable => 'This store is no longer available.';

  @override
  String get storeOpen => 'Open';

  @override
  String get storeClosed => 'Closed';

  @override
  String get pickup => 'Pickup';

  @override
  String get delivery => 'Delivery';

  @override
  String get sessionComplete => 'Session Complete';

  @override
  String thanksForOrdering(Object storeName) {
    return 'Thanks for ordering at $storeName';
  }

  @override
  String get orderSummary => 'Order Summary';

  @override
  String get item => 'Item';

  @override
  String get subtotal => 'Subtotal';

  @override
  String get tax => 'Tax';

  @override
  String get total => 'Total';

  @override
  String get noItemsOrdered => 'No items were ordered.';

  @override
  String get howWasExperience => 'How was your experience?';

  @override
  String get thanksForFeedback => 'Thanks for your feedback!';

  @override
  String get newOrder => 'New Order';

  @override
  String get about => 'About';

  @override
  String get appName => 'App Name';

  @override
  String get appNameValue => 'VoxEats';

  @override
  String get version => 'Version';

  @override
  String get themeSignature => 'Signature';

  @override
  String get themeLight => 'Light';

  @override
  String get themeDark => 'Dark';

  @override
  String get themeOcean => 'Ocean';

  @override
  String get themeSunset => 'Sunset';

  @override
  String get themeForest => 'Forest';

  @override
  String get themeContrast => 'Contrast';
}
