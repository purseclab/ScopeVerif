package com.abc.storage_verifier.uri_api.access_uri_api

import android.net.Uri
import android.util.Base64
import android.util.Log
import androidx.appcompat.app.AppCompatActivity
import com.abc.storage_verifier.*
import java.io.File
import java.io.FileOutputStream
import java.nio.charset.Charset


class IOStreamApi(context: AppCompatActivity): AccessUriApi(context) {
    override fun write(uri: Uri, content: String): ApiResult<String?> {
        var succeed = false
        var path: String? = null
        val msg = CustomException.getThrowableResultWithFeedback {
            context.contentResolver.openOutputStream(uri, "wt")?.use { outputStream ->
                if (content.startsWith("Base64:")) {
                    val base64Content = content.substring(7)
                    outputStream.write(Base64.decode(base64Content, Base64.DEFAULT))
                } else {
                    outputStream.write(content.toByteArray())
                }
                path = PathUriHelper.getPathFromUri(context, uri)
            }
            path = PathUriHelper.getPathFromUri(context, uri)
            if(path != null){
                succeed = true
            }
            succeed
        }
        return ApiResult(succeed, path, msg)
    }

    override fun read(uri: Uri): ApiResult<String?> {
        var succeed = false
        var content: String? = null
        val msg = CustomException.getThrowableResultWithFeedback {
            content = try {
                val originalContentUri = PathUriHelper.getOriginalUri(uri)
                readContentByUri(originalContentUri)
            } catch (e: Exception) {
                when (e) {
                    is SecurityException, is UnsupportedOperationException -> {
                        Log.d("FILE", "Permission denied, location data stripped!")
                        readContentByUri(uri)
                    }
                    else -> throw e
                }
            }

            succeed = true
            succeed
        }

        return ApiResult(succeed, content, msg)
    }

    private fun readContentByUri(uri: Uri): String {
        var result = ""
        context.contentResolver.openInputStream(uri)?.use { inputStream ->
            val readData = inputStream.readBytes()
            result = if (!isPlaintext(readData)) {
                "Base64:" + Base64.encodeToString(readData, Base64.DEFAULT)
            } else {
                readData.toString(Charset.defaultCharset())
            }
        }
        return result
    }

}