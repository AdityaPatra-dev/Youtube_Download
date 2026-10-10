package com.adityapatra.youtubedownloader;

import android.app.DownloadManager;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.util.Log;
import android.webkit.ConsoleMessage;
import android.webkit.JavascriptInterface;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Toast;
import androidx.appcompat.app.AppCompatActivity;
import androidx.webkit.WebViewAssetLoader;

import com.chaquo.python.PyObject;
import com.chaquo.python.Python;
import com.chaquo.python.android.AndroidPlatform;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.File;
import java.text.SimpleDateFormat;
import java.util.Arrays;
import java.util.Date;
import java.util.Locale;

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

        // 5. Connect direct in-process listener for zero-latency progress updates
        DownloadService.listener = new DownloadService.DownloadListener() {
            @Override
            public void onProgress(String data) {
                runOnUiThread(() -> {
                    if (webView != null) {
                        webView.evaluateJavascript("if (window.onMobileProgress) { window.onMobileProgress(" + data + "); }", null);
                    }
                });
            }

            @Override
            public void onLog(String msg) {
                runOnUiThread(() -> {
                    if (webView != null) {
                        webView.evaluateJavascript("if (window.onMobileLog) { window.onMobileLog(" + JSONObjectEscape(msg) + "); }", null);
                    }
                });
            }

            @Override
            public void onComplete(String data) {
                runOnUiThread(() -> {
                    if (webView != null) {
                        webView.evaluateJavascript("if (window.onMobileComplete) { window.onMobileComplete(" + data + "); }", null);
                    }
                });
            }

            @Override
            public void onError(String error) {
                runOnUiThread(() -> {
                    if (webView != null) {
                        webView.evaluateJavascript("if (window.onMobileError) { window.onMobileError(" + JSONObjectEscape(error) + "); }", null);
                    }
                });
            }
        };

        // 6. Load local frontend via secure asset loader
        webView.loadUrl("https://appassets.androidplatform.net/assets/web/index.html");

        // 7. Register broadcast receiver as secondary fallback
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
        DownloadService.listener = null;
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

        @JavascriptInterface
        public void openDownloadsFolder() {
            try {
                Intent intent = new Intent(DownloadManager.ACTION_VIEW_DOWNLOADS);
                intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                startActivity(intent);
            } catch (Exception e) {
                try {
                    Intent intent = new Intent(Intent.ACTION_VIEW);
                    Uri uri = Uri.parse(Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS).getAbsolutePath());
                    intent.setDataAndType(uri, "*/*");
                    intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                    startActivity(intent);
                } catch (Exception ex) {
                    runOnUiThread(() -> Toast.makeText(MainActivity.this, "Saved to Downloads folder: " + Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS).getAbsolutePath(), Toast.LENGTH_LONG).show());
                }
            }
        }

        @JavascriptInterface
        public String getDownloadedFiles() {
            try {
                File dir = Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS);
                JSONArray arr = new JSONArray();
                if (dir.exists() && dir.isDirectory()) {
                    File[] files = dir.listFiles((d, name) -> {
                        String n = name.toLowerCase();
                        return n.endsWith(".mp4") || n.endsWith(".m4a") || n.endsWith(".mp3")
                                || n.endsWith(".webm") || n.endsWith(".mkv") || n.endsWith(".flac");
                    });
                    if (files != null) {
                        Arrays.sort(files, (a, b) -> Long.compare(b.lastModified(), a.lastModified()));
                        SimpleDateFormat sdf = new SimpleDateFormat("MMM d, HH:mm", Locale.getDefault());
                        for (File f : files) {
                            JSONObject obj = new JSONObject();
                            obj.put("name", f.getName());
                            long bytes = f.length();
                            String szStr;
                            if (bytes >= 1024 * 1024 * 1024) szStr = String.format(Locale.US, "%.1f GB", bytes / (1024.0 * 1024.0 * 1024.0));
                            else if (bytes >= 1024 * 1024) szStr = String.format(Locale.US, "%.1f MB", bytes / (1024.0 * 1024.0));
                            else szStr = String.format(Locale.US, "%d KB", bytes / 1024);
                            obj.put("size_formatted", szStr);
                            obj.put("modified", sdf.format(new Date(f.lastModified())));
                            arr.put(obj);
                        }
                    }
                }
                return arr.toString();
            } catch (Exception e) {
                return "[]";
            }
        }
    }
}
