# Proguard rules for YouTube Downloader
-keep class com.adityapatra.youtubedownloader.** { *; }
-keepclassmembers class * {
    @android.webkit.JavascriptInterface <methods>;
}
