// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for Chinese (`zh`).
class AppLocalizationsZh extends AppLocalizations {
  AppLocalizationsZh([String locale = 'zh']) : super(locale);

  @override
  String get appTitle => '点餐';

  @override
  String get storesTitle => '店铺';

  @override
  String get pickStore => '今天想吃什么？';

  @override
  String get storeId => '店铺ID';

  @override
  String get storeName => '店铺名称';

  @override
  String get openVoiceOrder => '进入语音点餐';

  @override
  String get settingsTitle => '设置';

  @override
  String get appearanceTitle => '外观';

  @override
  String get themeTitle => '主题';

  @override
  String get languageTitle => '语言';

  @override
  String get authTitle => '登录以继续';

  @override
  String get login => '登录';

  @override
  String get signup => '注册';

  @override
  String get email => '邮箱';

  @override
  String get password => '密码';

  @override
  String get continueAsGuest => '以访客继续';

  @override
  String get guestModeEnabled => '已启用访客模式。';

  @override
  String get voiceTitle => '语音点餐';

  @override
  String get listening => '正在聆听…';

  @override
  String get connecting => '连接中…';

  @override
  String get tapMicToStart => '点击麦克风开始';

  @override
  String get whatAreYouCraving => '想吃\n什么？';

  @override
  String get goodMorning => '早上好';

  @override
  String get goodAfternoon => '下午好';

  @override
  String get goodEvening => '晚上好';

  @override
  String get searchRestaurants => '搜索餐厅...';

  @override
  String get nearbyRestaurants => '附近餐厅';

  @override
  String get somethingWentWrong => '出了点问题';

  @override
  String get tryAgain => '重试';

  @override
  String get noMatchesFound => '未找到匹配结果';

  @override
  String get noRestaurantsYet => '暂无餐厅';

  @override
  String get storeOpen => '营业中';

  @override
  String get storeClosed => '已关闭';

  @override
  String get pickup => '自取';

  @override
  String get delivery => '配送';

  @override
  String get sessionComplete => '会话完成';

  @override
  String thanksForOrdering(Object storeName) {
    return '感谢在 $storeName 下单';
  }

  @override
  String get orderSummary => '订单摘要';

  @override
  String get item => '商品';

  @override
  String get subtotal => '小计';

  @override
  String get tax => '税费';

  @override
  String get total => '合计';

  @override
  String get noItemsOrdered => '未点任何商品。';

  @override
  String get howWasExperience => '体验如何？';

  @override
  String get thanksForFeedback => '感谢您的反馈！';

  @override
  String get newOrder => '新订单';

  @override
  String get about => '关于';

  @override
  String get appName => '应用名称';

  @override
  String get appNameValue => 'Resto AI';

  @override
  String get version => '版本';

  @override
  String get themeSignature => '招牌';

  @override
  String get themeLight => '浅色';

  @override
  String get themeDark => '深色';

  @override
  String get themeOcean => '海洋';

  @override
  String get themeSunset => '日落';

  @override
  String get themeForest => '森林';

  @override
  String get themeContrast => '高对比';
}
