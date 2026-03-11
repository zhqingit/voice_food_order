import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:intl/intl.dart' as intl;

import 'app_localizations_en.dart';
import 'app_localizations_es.dart';
import 'app_localizations_zh.dart';

// ignore_for_file: type=lint

/// Callers can lookup localized strings with an instance of AppLocalizations
/// returned by `AppLocalizations.of(context)`.
///
/// Applications need to include `AppLocalizations.delegate()` in their app's
/// `localizationDelegates` list, and the locales they support in the app's
/// `supportedLocales` list. For example:
///
/// ```dart
/// import 'gen_l10n/app_localizations.dart';
///
/// return MaterialApp(
///   localizationsDelegates: AppLocalizations.localizationsDelegates,
///   supportedLocales: AppLocalizations.supportedLocales,
///   home: MyApplicationHome(),
/// );
/// ```
///
/// ## Update pubspec.yaml
///
/// Please make sure to update your pubspec.yaml to include the following
/// packages:
///
/// ```yaml
/// dependencies:
///   # Internationalization support.
///   flutter_localizations:
///     sdk: flutter
///   intl: any # Use the pinned version from flutter_localizations
///
///   # Rest of dependencies
/// ```
///
/// ## iOS Applications
///
/// iOS applications define key application metadata, including supported
/// locales, in an Info.plist file that is built into the application bundle.
/// To configure the locales supported by your app, you’ll need to edit this
/// file.
///
/// First, open your project’s ios/Runner.xcworkspace Xcode workspace file.
/// Then, in the Project Navigator, open the Info.plist file under the Runner
/// project’s Runner folder.
///
/// Next, select the Information Property List item, select Add Item from the
/// Editor menu, then select Localizations from the pop-up menu.
///
/// Select and expand the newly-created Localizations item then, for each
/// locale your application supports, add a new item and select the locale
/// you wish to add from the pop-up menu in the Value field. This list should
/// be consistent with the languages listed in the AppLocalizations.supportedLocales
/// property.
abstract class AppLocalizations {
  AppLocalizations(String locale)
    : localeName = intl.Intl.canonicalizedLocale(locale.toString());

  final String localeName;

  static AppLocalizations? of(BuildContext context) {
    return Localizations.of<AppLocalizations>(context, AppLocalizations);
  }

  static const LocalizationsDelegate<AppLocalizations> delegate =
      _AppLocalizationsDelegate();

  /// A list of this localizations delegate along with the default localizations
  /// delegates.
  ///
  /// Returns a list of localizations delegates containing this delegate along with
  /// GlobalMaterialLocalizations.delegate, GlobalCupertinoLocalizations.delegate,
  /// and GlobalWidgetsLocalizations.delegate.
  ///
  /// Additional delegates can be added by appending to this list in
  /// MaterialApp. This list does not have to be used at all if a custom list
  /// of delegates is preferred or required.
  static const List<LocalizationsDelegate<dynamic>> localizationsDelegates =
      <LocalizationsDelegate<dynamic>>[
        delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
      ];

  /// A list of this localizations delegate's supported locales.
  static const List<Locale> supportedLocales = <Locale>[
    Locale('en'),
    Locale('zh'),
    Locale('es'),
  ];

  /// No description provided for @appTitle.
  ///
  /// In en, this message translates to:
  /// **'VoxEats'**
  String get appTitle;

  /// No description provided for @storesTitle.
  ///
  /// In en, this message translates to:
  /// **'Stores'**
  String get storesTitle;

  /// No description provided for @pickStore.
  ///
  /// In en, this message translates to:
  /// **'What are you craving today?'**
  String get pickStore;

  /// No description provided for @storeId.
  ///
  /// In en, this message translates to:
  /// **'Store ID'**
  String get storeId;

  /// No description provided for @storeName.
  ///
  /// In en, this message translates to:
  /// **'Store name'**
  String get storeName;

  /// No description provided for @openVoiceOrder.
  ///
  /// In en, this message translates to:
  /// **'Open voice order'**
  String get openVoiceOrder;

  /// No description provided for @settingsTitle.
  ///
  /// In en, this message translates to:
  /// **'Settings'**
  String get settingsTitle;

  /// No description provided for @appearanceTitle.
  ///
  /// In en, this message translates to:
  /// **'Appearance'**
  String get appearanceTitle;

  /// No description provided for @themeTitle.
  ///
  /// In en, this message translates to:
  /// **'Theme'**
  String get themeTitle;

  /// No description provided for @languageTitle.
  ///
  /// In en, this message translates to:
  /// **'Language'**
  String get languageTitle;

  /// No description provided for @authTitle.
  ///
  /// In en, this message translates to:
  /// **'Sign in to continue'**
  String get authTitle;

  /// No description provided for @login.
  ///
  /// In en, this message translates to:
  /// **'Login'**
  String get login;

  /// No description provided for @signup.
  ///
  /// In en, this message translates to:
  /// **'Sign up'**
  String get signup;

  /// No description provided for @email.
  ///
  /// In en, this message translates to:
  /// **'Email'**
  String get email;

  /// No description provided for @password.
  ///
  /// In en, this message translates to:
  /// **'Password'**
  String get password;

  /// No description provided for @continueAsGuest.
  ///
  /// In en, this message translates to:
  /// **'Continue as Guest'**
  String get continueAsGuest;

  /// No description provided for @guestModeEnabled.
  ///
  /// In en, this message translates to:
  /// **'Guest mode enabled.'**
  String get guestModeEnabled;

  /// No description provided for @voiceTitle.
  ///
  /// In en, this message translates to:
  /// **'Voice order'**
  String get voiceTitle;

  /// No description provided for @listening.
  ///
  /// In en, this message translates to:
  /// **'Listening…'**
  String get listening;

  /// No description provided for @connecting.
  ///
  /// In en, this message translates to:
  /// **'Connecting…'**
  String get connecting;

  /// No description provided for @tapMicToStart.
  ///
  /// In en, this message translates to:
  /// **'Tap the mic to start'**
  String get tapMicToStart;

  /// No description provided for @whatAreYouCraving.
  ///
  /// In en, this message translates to:
  /// **'What are you\ncraving?'**
  String get whatAreYouCraving;

  /// No description provided for @goodMorning.
  ///
  /// In en, this message translates to:
  /// **'Good morning'**
  String get goodMorning;

  /// No description provided for @goodAfternoon.
  ///
  /// In en, this message translates to:
  /// **'Good afternoon'**
  String get goodAfternoon;

  /// No description provided for @goodEvening.
  ///
  /// In en, this message translates to:
  /// **'Good evening'**
  String get goodEvening;

  /// No description provided for @searchRestaurants.
  ///
  /// In en, this message translates to:
  /// **'Search restaurants...'**
  String get searchRestaurants;

  /// No description provided for @nearbyRestaurants.
  ///
  /// In en, this message translates to:
  /// **'Nearby Restaurants'**
  String get nearbyRestaurants;

  /// No description provided for @somethingWentWrong.
  ///
  /// In en, this message translates to:
  /// **'Something went wrong'**
  String get somethingWentWrong;

  /// No description provided for @tryAgain.
  ///
  /// In en, this message translates to:
  /// **'Try Again'**
  String get tryAgain;

  /// No description provided for @noMatchesFound.
  ///
  /// In en, this message translates to:
  /// **'No matches found'**
  String get noMatchesFound;

  /// No description provided for @noRestaurantsYet.
  ///
  /// In en, this message translates to:
  /// **'No restaurants yet'**
  String get noRestaurantsYet;

  /// No description provided for @storeUnavailable.
  ///
  /// In en, this message translates to:
  /// **'This store is no longer available.'**
  String get storeUnavailable;

  /// No description provided for @storeOpen.
  ///
  /// In en, this message translates to:
  /// **'Open'**
  String get storeOpen;

  /// No description provided for @storeClosed.
  ///
  /// In en, this message translates to:
  /// **'Closed'**
  String get storeClosed;

  /// No description provided for @pickup.
  ///
  /// In en, this message translates to:
  /// **'Pickup'**
  String get pickup;

  /// No description provided for @delivery.
  ///
  /// In en, this message translates to:
  /// **'Delivery'**
  String get delivery;

  /// No description provided for @sessionComplete.
  ///
  /// In en, this message translates to:
  /// **'Session Complete'**
  String get sessionComplete;

  /// No description provided for @thanksForOrdering.
  ///
  /// In en, this message translates to:
  /// **'Thanks for ordering at {storeName}'**
  String thanksForOrdering(Object storeName);

  /// No description provided for @orderSummary.
  ///
  /// In en, this message translates to:
  /// **'Order Summary'**
  String get orderSummary;

  /// No description provided for @item.
  ///
  /// In en, this message translates to:
  /// **'Item'**
  String get item;

  /// No description provided for @subtotal.
  ///
  /// In en, this message translates to:
  /// **'Subtotal'**
  String get subtotal;

  /// No description provided for @tax.
  ///
  /// In en, this message translates to:
  /// **'Tax'**
  String get tax;

  /// No description provided for @total.
  ///
  /// In en, this message translates to:
  /// **'Total'**
  String get total;

  /// No description provided for @noItemsOrdered.
  ///
  /// In en, this message translates to:
  /// **'No items were ordered.'**
  String get noItemsOrdered;

  /// No description provided for @howWasExperience.
  ///
  /// In en, this message translates to:
  /// **'How was your experience?'**
  String get howWasExperience;

  /// No description provided for @thanksForFeedback.
  ///
  /// In en, this message translates to:
  /// **'Thanks for your feedback!'**
  String get thanksForFeedback;

  /// No description provided for @newOrder.
  ///
  /// In en, this message translates to:
  /// **'New Order'**
  String get newOrder;

  /// No description provided for @about.
  ///
  /// In en, this message translates to:
  /// **'About'**
  String get about;

  /// No description provided for @appName.
  ///
  /// In en, this message translates to:
  /// **'App Name'**
  String get appName;

  /// No description provided for @appNameValue.
  ///
  /// In en, this message translates to:
  /// **'VoxEats'**
  String get appNameValue;

  /// No description provided for @version.
  ///
  /// In en, this message translates to:
  /// **'Version'**
  String get version;

  /// No description provided for @themeSignature.
  ///
  /// In en, this message translates to:
  /// **'Signature'**
  String get themeSignature;

  /// No description provided for @themeLight.
  ///
  /// In en, this message translates to:
  /// **'Light'**
  String get themeLight;

  /// No description provided for @themeDark.
  ///
  /// In en, this message translates to:
  /// **'Dark'**
  String get themeDark;

  /// No description provided for @themeOcean.
  ///
  /// In en, this message translates to:
  /// **'Ocean'**
  String get themeOcean;

  /// No description provided for @themeSunset.
  ///
  /// In en, this message translates to:
  /// **'Sunset'**
  String get themeSunset;

  /// No description provided for @themeForest.
  ///
  /// In en, this message translates to:
  /// **'Forest'**
  String get themeForest;

  /// No description provided for @themeContrast.
  ///
  /// In en, this message translates to:
  /// **'Contrast'**
  String get themeContrast;
}

class _AppLocalizationsDelegate
    extends LocalizationsDelegate<AppLocalizations> {
  const _AppLocalizationsDelegate();

  @override
  Future<AppLocalizations> load(Locale locale) {
    return SynchronousFuture<AppLocalizations>(lookupAppLocalizations(locale));
  }

  @override
  bool isSupported(Locale locale) =>
      <String>['en', 'es', 'zh'].contains(locale.languageCode);

  @override
  bool shouldReload(_AppLocalizationsDelegate old) => false;
}

AppLocalizations lookupAppLocalizations(Locale locale) {
  // Lookup logic when only language code is specified.
  switch (locale.languageCode) {
    case 'en':
      return AppLocalizationsEn();
    case 'es':
      return AppLocalizationsEs();
    case 'zh':
      return AppLocalizationsZh();
  }

  throw FlutterError(
    'AppLocalizations.delegate failed to load unsupported locale "$locale". This is likely '
    'an issue with the localizations generation tool. Please file an issue '
    'on GitHub with a reproducible sample app and the gen-l10n configuration '
    'that was used.',
  );
}
