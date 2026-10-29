package com.adityapatra.youtubedownloader;

import android.media.MediaCodec;
import android.media.MediaExtractor;
import android.media.MediaFormat;
import android.media.MediaMuxer;
import android.util.Log;

import java.io.File;
import java.nio.ByteBuffer;

/**
 * High-performance, hardware-accelerated Media Muxer for Android.
 * Remuxes separate video and audio elementary streams into a single MP4/WebM file
 * using Android's native MediaMuxer (libstagefright) with zero transcoding,
 * zero subprocesses, and zero external FFmpeg dependencies.
 */
public class MediaMuxerHelper {

    private static final String TAG = "MediaMuxerHelper";

    public static boolean mux(String videoPath, String audioPath, String outputPath) {
        MediaExtractor videoExtractor = null;
        MediaExtractor audioExtractor = null;
        MediaMuxer muxer = null;

        try {
            File vFile = new File(videoPath);
            File aFile = new File(audioPath);
            if (!vFile.exists() || !aFile.exists()) {
                Log.e(TAG, "Input stream file not found. Video exists: " + vFile.exists() + ", Audio exists: " + aFile.exists());
                return false;
            }

            // 1. Probe video track
            videoExtractor = new MediaExtractor();
            videoExtractor.setDataSource(videoPath);
            int videoTrackIndex = -1;
            int numVideoTracks = videoExtractor.getTrackCount();
            for (int i = 0; i < numVideoTracks; i++) {
                MediaFormat format = videoExtractor.getTrackFormat(i);
                String mime = format.getString(MediaFormat.KEY_MIME);
                if (mime != null && mime.startsWith("video/")) {
                    videoTrackIndex = i;
                    break;
                }
            }

            if (videoTrackIndex < 0) {
                Log.e(TAG, "No video track found in " + videoPath);
                return false;
            }

            // 2. Probe audio track
            audioExtractor = new MediaExtractor();
            audioExtractor.setDataSource(audioPath);
            int audioTrackIndex = -1;
            int numAudioTracks = audioExtractor.getTrackCount();
            for (int i = 0; i < numAudioTracks; i++) {
                MediaFormat format = audioExtractor.getTrackFormat(i);
                String mime = format.getString(MediaFormat.KEY_MIME);
                if (mime != null && mime.startsWith("audio/")) {
                    audioTrackIndex = i;
                    break;
                }
            }

            if (audioTrackIndex < 0) {
                Log.e(TAG, "No audio track found in " + audioPath);
                return false;
            }

            // 3. Prepare destination file
            File outFile = new File(outputPath);
            if (outFile.exists()) {
                outFile.delete();
            }

            int outputFormat = MediaMuxer.OutputFormat.MUXER_OUTPUT_MPEG_4;
            if (outputPath.toLowerCase().endsWith(".webm")) {
                outputFormat = MediaMuxer.OutputFormat.MUXER_OUTPUT_WEBM;
            }

            muxer = new MediaMuxer(outputPath, outputFormat);

            MediaFormat videoFormat = videoExtractor.getTrackFormat(videoTrackIndex);
            MediaFormat audioFormat = audioExtractor.getTrackFormat(audioTrackIndex);

            int muxerVideoTrack = muxer.addTrack(videoFormat);
            int muxerAudioTrack = muxer.addTrack(audioFormat);

            muxer.start();

            // 4. Copy video frames
            videoExtractor.selectTrack(videoTrackIndex);
            int videoBufSize = 2 * 1024 * 1024;
            if (videoFormat.containsKey(MediaFormat.KEY_MAX_INPUT_SIZE)) {
                int keySize = videoFormat.getInteger(MediaFormat.KEY_MAX_INPUT_SIZE);
                if (keySize > videoBufSize) videoBufSize = keySize;
            }
            ByteBuffer videoBuffer = ByteBuffer.allocateDirect(videoBufSize);
            MediaCodec.BufferInfo videoBufferInfo = new MediaCodec.BufferInfo();

            long lastVideoTimeUs = -1;
            while (true) {
                int sampleSize = videoExtractor.readSampleData(videoBuffer, 0);
                if (sampleSize < 0) {
                    break;
                }
                long timeUs = videoExtractor.getSampleTime();
                if (timeUs < 0) timeUs = 0;
                if (timeUs <= lastVideoTimeUs) {
                    timeUs = lastVideoTimeUs + 1000; // Monotonic timestamp guarantee
                }
                lastVideoTimeUs = timeUs;

                videoBufferInfo.offset = 0;
                videoBufferInfo.size = sampleSize;
                videoBufferInfo.presentationTimeUs = timeUs;
                videoBufferInfo.flags = videoExtractor.getSampleFlags();

                muxer.writeSampleData(muxerVideoTrack, videoBuffer, videoBufferInfo);
                videoExtractor.advance();
            }

            // 5. Copy audio frames
            audioExtractor.selectTrack(audioTrackIndex);
            int audioBufSize = 1024 * 1024;
            if (audioFormat.containsKey(MediaFormat.KEY_MAX_INPUT_SIZE)) {
                int keySize = audioFormat.getInteger(MediaFormat.KEY_MAX_INPUT_SIZE);
                if (keySize > audioBufSize) audioBufSize = keySize;
            }
            ByteBuffer audioBuffer = ByteBuffer.allocateDirect(audioBufSize);
            MediaCodec.BufferInfo audioBufferInfo = new MediaCodec.BufferInfo();

            long lastAudioTimeUs = -1;
            while (true) {
                int sampleSize = audioExtractor.readSampleData(audioBuffer, 0);
                if (sampleSize < 0) {
                    break;
                }
                long timeUs = audioExtractor.getSampleTime();
                if (timeUs < 0) timeUs = 0;
                if (timeUs <= lastAudioTimeUs) {
                    timeUs = lastAudioTimeUs + 1000; // Monotonic timestamp guarantee
                }
                lastAudioTimeUs = timeUs;

                audioBufferInfo.offset = 0;
                audioBufferInfo.size = sampleSize;
                audioBufferInfo.presentationTimeUs = timeUs;
                audioBufferInfo.flags = audioExtractor.getSampleFlags();

                muxer.writeSampleData(muxerAudioTrack, audioBuffer, audioBufferInfo);
                audioExtractor.advance();
            }

            muxer.stop();
            Log.i(TAG, "Remuxing completed successfully: " + outputPath);
            return true;

        } catch (Exception e) {
            Log.e(TAG, "MediaMuxer failed: " + e.getMessage(), e);
            return false;
        } finally {
            if (muxer != null) {
                try {
                    muxer.release();
                } catch (Exception ignored) {}
            }
            if (videoExtractor != null) {
                try {
                    videoExtractor.release();
                } catch (Exception ignored) {}
            }
            if (audioExtractor != null) {
                try {
                    audioExtractor.release();
                } catch (Exception ignored) {}
            }
        }
    }
}

