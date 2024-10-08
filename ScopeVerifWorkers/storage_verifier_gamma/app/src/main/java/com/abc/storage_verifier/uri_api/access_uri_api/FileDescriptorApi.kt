package com.abc.storage_verifier.uri_api.access_uri_api

import android.net.Uri
import android.util.Base64
import android.util.Log
import androidx.appcompat.app.AppCompatActivity
import com.abc.storage_verifier.*
import java.io.File
import java.io.FileInputStream
import java.io.FileOutputStream
import java.nio.charset.Charset


class FileDescriptorApi(context: AppCompatActivity): AccessUriApi(context) {
    fun readContentByUri(uri: Uri): String{
        var result = ""
        context.contentResolver.openFileDescriptor(uri, "r")?.use { parcelFileDescriptor ->
            FileInputStream(parcelFileDescriptor.fileDescriptor).use { inputStream ->
                val readData = inputStream.readBytes()
                if (!isPlaintext(readData)) {
                    result = "Base64:" + Base64.encodeToString(readData, Base64.DEFAULT)
                } else {
                    result = readData.toString(Charset.defaultCharset())
                }
            }
        }
        return result
    }
    override fun read(uri: Uri): ApiResult<String?> {
        var succeed = false
        var result: String? = null
        val msg = CustomException.getThrowableResultWithFeedback {
            result = try {
                val originalContentUri = PathUriHelper.getOriginalUri(uri)
                readContentByUri(originalContentUri)
            }catch (e: Exception) {
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

        return ApiResult(succeed, result, msg)
    }


    override fun write(uri: Uri, content: String): ApiResult<String?> {
        var succeed = false
        var path: String? = null
        val msg = CustomException.getThrowableResultWithFeedback {
            context.contentResolver.openFileDescriptor(uri, "wt")?.use { parcelFileDescriptor ->
                FileOutputStream(parcelFileDescriptor.fileDescriptor).use {
                    if(content.startsWith("Base64:")){
                        val base64Content = content.substring(7)
                        it.write(Base64.decode(base64Content, Base64.DEFAULT))
                    }else{
                        it.write(content.toByteArray())
                    }
                }
            }
            path = PathUriHelper.getPathFromUri(context, uri)
            if(path != null){
                succeed = true
            }
            succeed
        }

        return ApiResult(succeed, path, msg)
    }

}