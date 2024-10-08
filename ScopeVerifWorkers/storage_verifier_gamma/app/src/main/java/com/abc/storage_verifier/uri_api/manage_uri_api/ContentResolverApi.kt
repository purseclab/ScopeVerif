package com.abc.storage_verifier.uri_api.manage_uri_api

import android.annotation.SuppressLint
import android.content.ContentValues
import android.net.Uri
import android.provider.MediaStore
import androidx.appcompat.app.AppCompatActivity
import com.abc.storage_verifier.*
import java.io.File


// DocumentFile (Access Uri) only supports delete and partial update
class ContentResolverApi(context: AppCompatActivity): ManageUriApi(context){

    override fun delete(uri: Uri): ApiResult<String?>{
        var succeed = false
        var result: String? = null
        val msg = CustomException.getThrowableResultWithFeedback {
            context.contentResolver.delete(uri, null, null)
            result = PathUriHelper.getPathFromUri(context, uri)
            if (result == null || !File(result!!).exists()){
                succeed = true
            }
            succeed
        }
        return ApiResult(succeed, result, msg)
    }

    @SuppressLint("Range")
    override fun getSize(uri: Uri): ApiResult<Long?> {
        var succeed = false
        var result: Long? = null
        val msg = CustomException.getThrowableResultWithFeedback {
            context.contentResolver.query(uri, arrayOf("_id", MediaStore.MediaColumns.SIZE),
                null, null, null)?.use { cursor ->
                while (cursor.moveToNext()) {
                    result = cursor.getLong(cursor.getColumnIndex(MediaStore.MediaColumns.SIZE))
                    if(result!! > 0){
                        succeed = true
                    }
                }
            }
            succeed
        }
        return ApiResult(succeed, result, msg)
    }

    @SuppressLint("Range")
    override fun getModifiedTime(uri: Uri): ApiResult<Long?> {
        var succeed = false
        var result: Long? = null
        val msg = CustomException.getThrowableResultWithFeedback{
            context.contentResolver.query(uri, arrayOf("_id", MediaStore.MediaColumns.DATE_MODIFIED),
                null, null, null)?.use { cursor ->
                while (cursor.moveToNext()) {
                    result = cursor.getLong(cursor.getColumnIndex(MediaStore.MediaColumns.DATE_MODIFIED))/1000
                    if(result!! > 0){
                        succeed = true
                    }
                }
            }
            succeed
        }
        return ApiResult(succeed, result, msg)
    }

    override fun rename(uri: Uri, to: String): ApiResult<String?> {
        var succeed = false
        var result: String? = null
        val msg = CustomException.getThrowableResultWithFeedback {
            val contentValues = ContentValues()
            contentValues.put(MediaStore.MediaColumns.DISPLAY_NAME, to.split("/").last())
            val rowsUpdated = context.contentResolver.update(uri, contentValues, null, null)
            result = PathUriHelper.getPathFromUri(context, uri)
            succeed = rowsUpdated > 0
            succeed
        }
        return ApiResult(succeed, result, msg)
    }

    // "to" here is the target file
    override fun move(from: Uri, to: Uri): ApiResult<String?> {
        var succeed = false
        var result: String? = null
        val msg = CustomException.getThrowableResultWithFeedback {
            val inputStream = context.contentResolver.openInputStream(from)
            val outputStream = context.contentResolver.openOutputStream(to)
            val buffer = ByteArray(1024)
            var length: Int
            while (inputStream?.read(buffer).also { length = it!! }!! > 0) {
                outputStream?.write(buffer, 0, length)
            }
            inputStream?.close()
            outputStream?.close()
            context.contentResolver.delete(from, null, null)
            result = PathUriHelper.getPathFromUri(context, to)
            if(result!=null){
                succeed = true
            }
            succeed
        }
        return ApiResult(succeed, result, msg)
    }
}

//
//    override fun updateFileInternal(
//        from: String,
//        to: String?,
//        data: String?
//    ): MutableMap<String, Any?> {
//        if (getUriApi == null) {
//            throw Exception("Get Uri Api Combo Pair Not Found")
//        }
//        val updateResults = mutableMapOf<String, Any?>()
//        updateResults["path"] = CustomException.getThrowableResultWithFeedback {
//            // content update is needed
//            if(data != null){
//                CustomException.getCustomExceptionMessage("NOT_SUPPORTED")
//            }else{
//                val fromFile = DocumentFile.fromFile(File(from))
//                // move is needed
//                if(to != null){
//                    fromFile.renameTo(to)
//                }
//                PathUriHelper.getPathFromUri(context, fromFile.uri)
//            }
//        }
//        updateResults["action"] = getActionResult(updateResults.values.joinToString())
//        return updateResults
//    }