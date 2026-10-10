package com.adityapatra.youtubedownloader;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.util.Log;
import android.webkit.ConsoleMessage;
import android.webkit.JavascriptInterface;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import androidx.appcompat.app.AppCompatActivity;
import androidx.webkit.WebViewAssetLoader;

import com.chaquo.python.PyObject;
import com.chaquo.python.Python;
import com.chaquo.python.android.AndroidPlatform;

public class MainActivity extends AppCompatActivity {

    private static final String TAG = "MainActivity";
    private WebView webView;
    private BroadcastReceiver downloadReceiver;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        // 1. Initialize embedded Python runtime
        if (!Python.isStarted()) {
            Python.start(new AndroidPlatform(this));
        }

        // 2. Setup full-screen native WebView
        webView = new WebView(this);
        setContentView(webView);

        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setAllowFileAccess(true);
        settings.setAllowContentAccess(true);
        settings.setDatabaseEnabled(true);
        settings.setMediaPlaybackRequiresUserGesture(false);

        // 3. Configure modern Android WebViewAssetLoader
        final WebViewAssetLoader assetLoader = new WebViewAssetLoader.Builder()
                .addPathHandler("/assets/", new WebViewAssetLoader.AssetsPathHandler(this))
                .build();

        webView.setWebViewClient(new WebViewClient() {
            @Override
            public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest request) {
                return assetLoader.shouldInterceptRequest(request.getUrl());
            }

            @Override
            @SuppressWarnings("deprecation")
            public WebResourceResponse shouldInterceptRequest(WebView view, String url) {
                return assetLoader.shouldInterceptRequest(Uri.parse(url));
            }
        });

        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public boolean onConsoleMessage(ConsoleMessage consoleMessage) {
                Log.d(TAG, "[WebView Console] " + consoleMessage.message() + " -- Line "
                        + consoleMessage.lineNumber() + " of " + consoleMessage.sourceId());
                return true;
            }
        });

        // 4. Inject JavaScript bridge
        webView.addJavascriptInterface(new WebAppInterface(), "AndroidBridge");

        // 5. Load local frontend via secure asset loader
        webView.loadUrl("https://appassets.androidplatform.net/assets/web/index.html");

        // 6. Register broadcast receiver for real-time progress updates from DownloadService
        downloadReceiver = new BroadcastReceiver() {
            @Override
            public void onReceive(Context context, Intent intent) {
                String type = intent.getStringExtra("type");
                String data = intent.getStringExtra("data");

                if ("progress".equals(type)) {
                    webView.evaluateJavascript("if (window.onMobileProgress) { window.onMobileProgress(" + data + "); }", null);
                } else if ("log".equals(type)) {
                    webView.evaluateJavascript("if (window.onMobileLog) { window.onMobileLog(" + JSONObjectEscape(data) + "); }", null);
                } else if ("complete".equals(type)) {
                    webView.evaluateJavascript("if (window.onMobileComplete) { window.onMobileComplete(" + data + "); }", null);
                } else if ("error".equals(type)) {
                    webView.evaluateJavascript("if (window.onMobileError) { window.onMobileError(" + JSONObjectEscape(data) + "); }", null);
                }
            }
        };

        IntentFilter filter = new IntentFilter("com.adityapatra.youtubedownloader.PROGRESS_UPDATE");
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            registerReceiver(downloadReceiver, filter, Context.RECEIVER_NOT_EXPORTED);
        } else {
            registerReceiver(downloadReceiver, filter);
        }

        // Handle shared URL from other apps (e.g. YouTube app share button)
        handleSendIntent(getIntent());
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        handleSendIntent(intent);
    }

    private void handleSendIntent(Intent intent) {
        if (intent != null && Intent.ACTION_SEND.equals(intent.getAction()) && "text/plain".equals(intent.getType())) {
            String sharedText = intent.getStringExtra(Intent.EXTRA_TEXT);
            if (sharedText != null) {
                webView.post(() -> {
                    webView.evaluateJavascript("if (window.setSharedUrl) { window.setSharedUrl('" + JSONObjectEscapeRaw(sharedText) + "'); }", null);
                });
            }
        }
    }

    private String JSONObjectEscape(String s) {
        if (s == null) return "\"\"";
        return "\"" + s.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n").replace("\r", "") + "\"";
    }

    private String JSONObjectEscapeRaw(String s) {
        if (s == null) return "";
        return s.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "").replace("\r", "");
    }

    @Override
    public void onBackPressed() {
        if (webView != null && webView.canGoBack()) {
            webView.goBack();
        } else {
            super.onBackPressed();
        }
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        if (downloadReceiver != null) {
            unregisterReceiver(downloadReceiver);
        }
    }

    public class WebAppInterface {

        @JavascriptInterface
        public String getSystemStatus() {
            return "{\"ytdlp_version\":\"Embedded Engine\",\"ffmpeg_available\":true,\"aria2c_available\":false,\"detected_browsers\":[]}";
        }

        @JavascriptInterface
        public String fetchInfo(String url, String cookies) {
            try {
                Python py = Python.getInstance();
                PyObject bridge = py.getModule("mobile_bridge");
                return bridge.callAttr("fetch_video_info", url, cookies != null ? cookies : "").toString();
            } catch (Exception e) {
                return "{\"error\":\"" + JSONObjectEscapeRaw(e.getMessage()) + "\"}";
            }
        }

        @JavascriptInterface
        public String fetchInfo(String url) {
            return fetchInfo(url, "");
        }

        @JavascriptInterface
        public void startDownload(String requestJson) {
            Intent serviceIntent = new Intent(MainActivity.this, DownloadService.class);
            serviceIntent.putExtra("request_json", requestJson);
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                startForegroundService(serviceIntent);
            } else {
                startService(serviceIntent);
            }
        }
    }
}
