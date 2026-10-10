package com.adityapatra.youtubedownloader;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.media.MediaScannerConnection;
import android.os.Build;
import android.os.Environment;
import android.os.IBinder;
import android.os.PowerManager;
import androidx.core.app.NotificationCompat;

import com.chaquo.python.PyObject;
import com.chaquo.python.Python;

import org.json.JSONObject;

import java.io.File;

public class DownloadService extends Service {

    private static final String CHANNEL_ID = "yt_download_channel";
    private static final int NOTIFICATION_ID = 1001;

    private PowerManager.WakeLock wakeLock;
    private NotificationManager notificationManager;

    @Override
    public void onCreate() {
        super.onCreate();

        notificationManager = (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
        createNotificationChannel();

        PowerManager powerManager = (PowerManager) getSystemService(Context.POWER_SERVICE);
        if (powerManager != null) {
            wakeLock = powerManager.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "YouTubeDownloader::DownloadWakeLock");
            wakeLock.acquire(1000 * 60 * 60); // Max 1 hour
        }
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        if (intent == null) return START_NOT_STICKY;

        String requestJson = intent.getStringExtra("request_json");

        // Start foreground service with initial notification
        Notification notification = buildNotification("Starting download...", 0);
        startForeground(NOTIFICATION_ID, notification);

        new Thread(() -> {
            try {
                // Ensure output directory is the public Android Downloads folder
                JSONObject reqObj = new JSONObject(requestJson);
                File publicDownloadDir = Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS);
                if (!publicDownloadDir.exists()) {
                    publicDownloadDir.mkdirs();
                }
                reqObj.put("output_dir", publicDownloadDir.getAbsolutePath());

                Python py = Python.getInstance();
                PyObject bridge = py.getModule("mobile_bridge");

                // Java callback interfaces for Chaquopy
                PyObject progressCb = PyObject.fromJava(new Callback() {
                    @Override
                    public void invoke(String data) {
                        try {
                            JSONObject obj = new JSONObject(data);
                            int percent = (int) obj.optDouble("percent", 0);
                            String speed = obj.optString("speed", "");
                            String filename = obj.optString("filename", "Media");

                            notificationManager.notify(NOTIFICATION_ID, buildNotification(filename + " (" + percent + "% • " + speed + ")", percent));
                            broadcastProgress("progress", data);
                        } catch (Exception ignored) {}
                    }
                });

                PyObject logCb = PyObject.fromJava(new Callback() {
                    @Override
                    public void invoke(String msg) {
                        broadcastProgress("log", msg);
                    }
                });

                PyObject completeCb = PyObject.fromJava(new Callback() {
                    @Override
                    public void invoke(String data) {
                        notificationManager.notify(NOTIFICATION_ID, buildNotification("Download Complete!", 100));
                        broadcastProgress("complete", data);

                        // Scan public Downloads folder so media player apps see the file immediately
                        MediaScannerConnection.scanFile(
                                DownloadService.this,
                                new String[]{publicDownloadDir.getAbsolutePath()},
                                null,
                                null
                        );

                        cleanup();
                    }
                });

                PyObject errorCb = PyObject.fromJava(new Callback() {
                    @Override
                    public void invoke(String error) {
                        notificationManager.notify(NOTIFICATION_ID, buildNotification("Download Error: " + error, 0));
                        broadcastProgress("error", error);
                        cleanup();
                    }
                });

                bridge.callAttr("start_download", reqObj.toString(), progressCb, logCb, completeCb, errorCb);

            } catch (Exception e) {
                broadcastProgress("error", e.getMessage());
                cleanup();
            }
        }).start();

        return START_NOT_STICKY;
    }

    private void broadcastProgress(String type, String data) {
        Intent broadcast = new Intent("com.adityapatra.youtubedownloader.PROGRESS_UPDATE");
        broadcast.putExtra("type", type);
        broadcast.putExtra("data", data);
        sendBroadcast(broadcast);
    }

    private Notification buildNotification(String text, int progress) {
        NotificationCompat.Builder builder = new NotificationCompat.Builder(this, CHANNEL_ID)
                .setContentTitle("YouTube Downloader")
                .setContentText(text)
                .setSmallIcon(android.R.drawable.stat_sys_download)
                .setOngoing(progress < 100 && progress > 0)
                .setOnlyAlertOnce(true)
                .setPriority(NotificationCompat.PRIORITY_LOW);

        if (progress > 0 && progress < 100) {
            builder.setProgress(100, progress, false);
        }

        return builder.build();
    }

    private void createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel channel = new NotificationChannel(
                    CHANNEL_ID,
                    "YouTube Downloads",
                    NotificationManager.IMPORTANCE_LOW
            );
            channel.setDescription("Background download progress and status");
            notificationManager.createNotificationChannel(channel);
        }
    }

    private void cleanup() {
        if (wakeLock != null && wakeLock.isHeld()) {
            wakeLock.release();
        }
        stopForeground(false);
        stopSelf();
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    public interface Callback {
        void invoke(String arg);
    }
}

