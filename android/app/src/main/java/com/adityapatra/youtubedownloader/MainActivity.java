package com.adityapatra.youtubedownloader;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.webkit.JavascriptInterface;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import androidx.appcompat.app.AppCompatActivity;

import com.chaquo.python.PyObject;
import com.chaquo.python.Python;
import com.chaquo.python.android.AndroidPlatform;

public class MainActivity extends AppCompatActivity {

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

        webView.setWebViewClient(new WebViewClient());
        webView.setWebChromeClient(new WebChromeClient());

        // 3. Inject JavaScript bridge
        webView.addJavascriptInterface(new WebAppInterface(), "AndroidBridge");

        // 4. Load local HTML/CSS/JS frontend
        webView.loadUrl("file:///android_asset/web/index.html");

        // 5. Register broadcast receiver for real-time progress updates from DownloadService
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
                    webView.evaluateJavascript("if (window.setSharedUrl) { window.setSharedUrl('" + sharedText + "'); }", null);
                });
            }
        }
    }

    private String JSONObjectEscape(String s) {
        if (s == null) return "\"\"";
        return "\"" + s.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n").replace("\r", "") + "\"";
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
        public String fetchInfo(String url) {
            try {
                Python py = Python.getInstance();
                PyObject bridge = py.getModule("mobile_bridge");
                return bridge.callAttr("fetch_video_info", url).toString();
            } catch (Exception e) {
                return "{\"error\":\"" + e.getMessage() + "\"}";
            }
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

