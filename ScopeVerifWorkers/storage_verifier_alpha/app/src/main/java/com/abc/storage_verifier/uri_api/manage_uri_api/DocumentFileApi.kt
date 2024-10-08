package com.abc.storage_verifier.uri_api.manage_uri_api

import android.content.Context
import android.net.Uri
import android.provider.DocumentsContract
import android.util.Log
import androidx.appcompat.app.AppCompatActivity
import androidx.documentfile.provider.DocumentFile
import com.abc.storage_verifier.ApiResult
import com.abc.storage_verifier.CustomException
import com.abc.storage_verifier.ManageUriApi
import com.abc.storage_verifier.PathUriHelper
import java.io.File
import java.io.InputStream
import java.io.OutputStream


// DocumentFile (Access Uri) only supports delete and partial update
class DocumentFileApi(context: AppCompatActivity): ManageUriApi(context){

    override fun delete(uri: Uri): ApiResult<String?>{
        var succeed = false
        var result : String? = null
        val msg = CustomException.getThrowableResultWithFeedback {
            DocumentFile.fromSingleUri(context, uri)?.delete()
            result = PathUriHelper.getPathFromUri(context, uri)
            if (result == null || !File(result!!).exists()){
                succeed = true
            }
            succeed
        }
        return ApiResult(succeed, result, msg)
    }

    override fun getSize(uri: Uri): ApiResult<Long?> {
        var succeed = false
        var result: Long? = null
        val msg = CustomException.getThrowableResultWithFeedback {
            result = DocumentFile.fromSingleUri(context, uri)?.length()
            if(result!! > 0){
                succeed = true
            }
            succeed
        }
        return ApiResult(succeed, result, msg)
    }

    override fun getModifiedTime(uri: Uri): ApiResult<Long?> {
        var succeed = false
        var result: Long? = null
        val msg = CustomException.getThrowableResultWithFeedback{
            result = DocumentFile.fromSingleUri(context, uri)?.lastModified()?.div(1000)
            if(result!! > 0){
                succeed = true
            }
            succeed
        }
        return ApiResult(succeed, result, msg)
    }

    override fun rename(uri: Uri, to: String): ApiResult<String?> {
        var succeed = false
        var result: String? = null
        val msg = CustomException.getThrowableResultWithFeedback {
            val filename = to.split("/").last()

            // DocumentFile doesn't support rename, so we borrow the rename function from DocumentsContract
            val newUri = DocumentsContract.renameDocument(context.contentResolver, uri, filename)!!
            result = PathUriHelper.getPathFromUri(context, newUri)
            if(result != null){
                succeed = true
            }
            succeed
        }
        return ApiResult(succeed, result, msg)
    }

    // "to" here is the target folder
    override fun move(from: Uri, to: Uri): ApiResult<String?> {
        var succeed = false
        var result: String? = null
        val msg = CustomException.getThrowableResultWithFeedback {
            val sourceFile = DocumentFile.fromSingleUri(context, from)
            val targetDirectory = DocumentFile.fromTreeUri(context, to)

            // Make sure that source file and target directory are not null
            if (sourceFile != null && targetDirectory != null) {
                val mimeType = sourceFile.type ?: "application/octet-stream"
                val targetFile = targetDirectory.createFile(mimeType, sourceFile.name ?: "unnamed")

                // Make sure that target file is not null
                if (targetFile != null) {
                    // Copy content
                    try {
                        val originalSourceFileUri = PathUriHelper.getOriginalUri(sourceFile.uri)
                        copyContent(context, originalSourceFileUri, targetFile.uri)
                    } catch (e: Exception) {
                        when (e) {
                            is SecurityException, is UnsupportedOperationException -> {
                                Log.d("FILE", "Exception occurred: ${e.message}")
                                copyContent(context, sourceFile.uri, targetFile.uri)
                            }
                            else -> throw e
                        }
                    }
                    // Delete the source file
                    sourceFile.delete()
                    result = PathUriHelper.getPathFromUri(context, targetFile.uri)
                    if(result != null){
                        succeed = true
                    }
                }
            }
            succeed
        }
        return ApiResult(succeed, result, msg)
    }

    // Copy the content of the source file into the destination file
    private fun copyContent(context: Context, sourceUri: Uri, destinationUri: Uri) {
        val inputStream: InputStream? = context.contentResolver.openInputStream(sourceUri)
        val outputStream: OutputStream? = context.contentResolver.openOutputStream(destinationUri)

        if (inputStream != null && outputStream != null) {
            inputStream.use { input ->
                outputStream.use { output ->
                    input.copyTo(output)
                }
            }
        }
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