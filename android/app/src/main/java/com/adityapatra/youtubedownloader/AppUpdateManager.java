package com.adityapatra.youtubedownloader;

import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageInfo;
import android.net.Uri;
import android.os.Build;
import android.os.Environment;
import android.os.Handler;
import android.os.Looper;
import android.provider.Settings;
import android.util.Log;
import android.widget.Toast;
import androidx.core.content.FileProvider;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;

public class AppUpdateManager {

    private static final String TAG = "AppUpdateManager";
    public static final String GITHUB_REPO = "AdityaPatra-dev/Youtube_Download";

    public static volatile File pendingInstallApk = null;
    private static final Handler mainHandler = new Handler(Looper.getMainLooper());

    public interface CheckCallback {
        void onResult(String jsonResult);
    }

    public interface DownloadCallback {
        void onProgress(int percent, long downloaded, long total);
        void onComplete(File apkFile);
        void onError(String error);
    }

    public static String getCurrentAppVersion(Context context) {
        try {
            PackageInfo pInfo = context.getPackageManager().getPackageInfo(context.getPackageName(), 0);
            return pInfo.versionName;
        } catch (Exception e) {
            return "1.4.1";
        }
    }

    public static int compareVersions(String v1, String v2) {
        if (v1 == null) v1 = "0.0.0";
        if (v2 == null) v2 = "0.0.0";
        v1 = v1.replaceAll("^[vV]", "").trim();
        v2 = v2.replaceAll("^[vV]", "").trim();

        String[] parts1 = v1.split("\\.");
        String[] parts2 = v2.split("\\.");
        int length = Math.max(parts1.length, parts2.length);

        for (int i = 0; i < length; i++) {
            int p1 = 0;
            if (i < parts1.length) {
                try {
                    p1 = Integer.parseInt(parts1[i].replaceAll("\\D.*", ""));
                } catch (Exception ignored) {}
            }
            int p2 = 0;
            if (i < parts2.length) {
                try {
                    p2 = Integer.parseInt(parts2[i].replaceAll("\\D.*", ""));
                } catch (Exception ignored) {}
            }
            if (p1 < p2) return -1;
            if (p1 > p2) return 1;
        }
        return 0;
    }

    public static void checkUpdate(Context context, CheckCallback callback) {
        new Thread(() -> {
            JSONObject res = new JSONObject();
            String currentVersion = getCurrentAppVersion(context);
            if (!currentVersion.startsWith("v")) currentVersion = "v" + currentVersion;

            try {
                String latestTag = null;
                String releaseNotes = "";
                String downloadUrl = null;

                // 1. First probe GitHub release redirect (100% immune to API rate-limiting)
                try {
                    URL redirectUrl = new URL("https://github.com/" + GITHUB_REPO + "/releases/latest");
                    HttpURLConnection conn = (HttpURLConnection) redirectUrl.openConnection();
                    conn.setInstanceFollowRedirects(false);
                    conn.setRequestProperty("User-Agent", "Mozilla/5.0");
                    conn.setConnectTimeout(6000);
                    conn.setReadTimeout(6000);
                    conn.connect();

                    String location = conn.getHeaderField("Location");
                    if (location != null && location.contains("/tag/")) {
                        latestTag = location.substring(location.lastIndexOf('/') + 1).trim();
                    }
                    conn.disconnect();
                } catch (Exception e) {
                    Log.w(TAG, "Redirect check failed: " + e.getMessage());
                }

                // 2. Query GitHub API for detailed release notes and assets if possible
                try {
                    URL apiUrl = new URL("https://api.github.com/repos/" + GITHUB_REPO + "/releases/latest");
                    HttpURLConnection apiConn = (HttpURLConnection) apiUrl.openConnection();
                    apiConn.setRequestProperty("User-Agent", "YouTubeDownloader-App");
                    apiConn.setRequestProperty("Accept", "application/vnd.github.v3+json");
                    apiConn.setConnectTimeout(6000);
                    apiConn.setReadTimeout(6000);

                    if (apiConn.getResponseCode() == 200) {
                        BufferedReader reader = new BufferedReader(new InputStreamReader(apiConn.getInputStream()));
                        StringBuilder sb = new StringBuilder();
                        String line;
                        while ((line = reader.readLine()) != null) {
                            sb.append(line);
                        }
                        reader.close();

                        JSONObject apiJson = new JSONObject(sb.toString());
                        if (latestTag == null || latestTag.isEmpty()) {
                            latestTag = apiJson.optString("tag_name");
                        }
                        releaseNotes = apiJson.optString("body", "");

                        JSONArray assets = apiJson.optJSONArray("assets");
                        if (assets != null) {
                            for (int i = 0; i < assets.length(); i++) {
                                JSONObject asset = assets.getJSONObject(i);
                                String name = asset.optString("name", "");
                                if (name.endsWith(".apk")) {
                                    downloadUrl = asset.optString("browser_download_url");
                                    break;
                                }
                            }
                        }
                    }
                    apiConn.disconnect();
                } catch (Exception e) {
                    Log.w(TAG, "GitHub API fetch exception: " + e.getMessage());
                }

                if (latestTag == null || latestTag.isEmpty()) {
                    latestTag = currentVersion;
                }
                if (!latestTag.startsWith("v")) {
                    latestTag = "v" + latestTag;
                }

                if (downloadUrl == null || downloadUrl.isEmpty()) {
                    downloadUrl = "https://github.com/" + GITHUB_REPO + "/releases/download/" + latestTag + "/YouTube-Downloader.apk";
                }

                boolean isUpdateAvailable = compareVersions(currentVersion, latestTag) < 0;

                res.put("status", "success");
                res.put("current_version", currentVersion);
                res.put("latest_version", latestTag);
                res.put("is_update_available", isUpdateAvailable);
                res.put("download_url", downloadUrl);
                res.put("release_notes", releaseNotes);

            } catch (Exception e) {
                try {
                    res.put("status", "error");
                    res.put("current_version", currentVersion);
                    res.put("message", e.getMessage());
                } catch (Exception ignored) {}
            }

            mainHandler.post(() -> callback.onResult(res.toString()));
        }).start();
    }

    public static void downloadAndInstall(Context context, String apkUrl, DownloadCallback callback) {
        new Thread(() -> {
            InputStream in = null;
            FileOutputStream out = null;
            HttpURLConnection conn = null;

            try {
                URL url = new URL(apkUrl);
                conn = (HttpURLConnection) url.openConnection();
                conn.setRequestProperty("User-Agent", "Mozilla/5.0");
                conn.setConnectTimeout(10000);
                conn.setReadTimeout(15000);
                conn.setInstanceFollowRedirects(true);
                conn.connect();

                // Handle redirects manually if needed
                int status = conn.getResponseCode();
                if (status == HttpURLConnection.HTTP_MOVED_TEMP || status == HttpURLConnection.HTTP_MOVED_PERM || status == 307 || status == 308) {
                    String newUrl = conn.getHeaderField("Location");
                    conn.disconnect();
                    url = new URL(newUrl);
                    conn = (HttpURLConnection) url.openConnection();
                    conn.setRequestProperty("User-Agent", "Mozilla/5.0");
                    conn.connect();
                }

                long totalBytes = conn.getContentLength();
                in = conn.getInputStream();

                File targetDir = context.getExternalFilesDir(Environment.DIRECTORY_DOWNLOADS);
                if (targetDir == null) {
                    targetDir = context.getCacheDir();
                }
                File apkFile = new File(targetDir, "YouTube-Downloader-update.apk");
                if (apkFile.exists()) {
                    apkFile.delete();
                }

                out = new FileOutputStream(apkFile);
                byte[] buffer = new byte[8192];
                long downloadedBytes = 0;
                int bytesRead;
                long lastProgressTime = 0;

                while ((bytesRead = in.read(buffer)) != -1) {
                    out.write(buffer, 0, bytesRead);
                    downloadedBytes += bytesRead;

                    long now = System.currentTimeMillis();
                    if (now - lastProgressTime >= 150 || (totalBytes > 0 && downloadedBytes == totalBytes)) {
                        lastProgressTime = now;
                        int percent = totalBytes > 0 ? (int) ((downloadedBytes * 100) / totalBytes) : 0;
                        long finalDownloaded = downloadedBytes;
                        long finalTotal = totalBytes;
                        mainHandler.post(() -> callback.onProgress(percent, finalDownloaded, finalTotal));
                    }
                }

                out.flush();
                out.close();
                out = null;

                mainHandler.post(() -> {
                    callback.onComplete(apkFile);
                    installApk(context, apkFile);
                });

            } catch (Exception e) {
                Log.e(TAG, "Update download failed: " + e.getMessage(), e);
                mainHandler.post(() -> callback.onError(e.getMessage() != null ? e.getMessage() : "Download error"));
            } finally {
                try { if (in != null) in.close(); } catch (Exception ignored) {}
                try { if (out != null) out.close(); } catch (Exception ignored) {}
                try { if (conn != null) conn.disconnect(); } catch (Exception ignored) {}
            }
        }).start();
    }

    public static void installApk(Context context, File apkFile) {
        if (apkFile == null || !apkFile.exists()) {
            Toast.makeText(context, "Update package not found", Toast.LENGTH_SHORT).show();
            return;
        }

        // Verify Android 8.0+ unknown app install permission
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            if (!context.getPackageManager().canRequestPackageInstalls()) {
                pendingInstallApk = apkFile;
                Toast.makeText(context, "Please allow permission to install updates", Toast.LENGTH_LONG).show();
                try {
                    Intent settingsIntent = new Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES);
                    settingsIntent.setData(Uri.parse("package:" + context.getPackageName()));
                    settingsIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                    context.startActivity(settingsIntent);
                } catch (Exception e) {
                    Intent fallbackIntent = new Intent(Settings.ACTION_SECURITY_SETTINGS);
                    fallbackIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                    context.startActivity(fallbackIntent);
                }
                return;
            }
        }

        try {
            Intent installIntent = new Intent(Intent.ACTION_VIEW);
            Uri apkUri = FileProvider.getUriForFile(
                    context,
                    context.getPackageName() + ".fileprovider",
                    apkFile
            );

            installIntent.setDataAndType(apkUri, "application/vnd.android.package-archive");
            installIntent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
            installIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            context.startActivity(installIntent);
        } catch (Exception e) {
            Log.e(TAG, "Failed to launch package installer: " + e.getMessage(), e);
            Toast.makeText(context, "Installation error: " + e.getMessage(), Toast.LENGTH_LONG).show();
        }
    }

    public static void resumePendingInstall(Context context) {
        if (pendingInstallApk != null && pendingInstallApk.exists()) {
            if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O || context.getPackageManager().canRequestPackageInstalls()) {
                File file = pendingInstallApk;
                pendingInstallApk = null;
                installApk(context, file);
            }
        }
    }
}

