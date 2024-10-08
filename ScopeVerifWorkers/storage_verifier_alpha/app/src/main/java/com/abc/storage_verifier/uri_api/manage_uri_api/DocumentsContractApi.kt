package com.abc.storage_verifier.uri_api.manage_uri_api

import android.annotation.SuppressLint
import android.content.ContentValues
import android.net.Uri
import android.provider.DocumentsContract
import android.util.Log
import androidx.appcompat.app.AppCompatActivity
import com.abc.storage_verifier.*
import java.io.File


class DocumentsContractApi(context: AppCompatActivity): ManageUriApi(context) {
    override fun delete(uri: Uri): ApiResult<String?>{
        var succeed = false
        var result:String? = null
        val msg = CustomException.getThrowableResultWithFeedback {
            DocumentsContract.deleteDocument(context.contentResolver, uri)
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
            context.contentResolver.query(uri, arrayOf("_id", DocumentsContract.Document.COLUMN_SIZE),
                null, null, null)?.use { cursor ->
                while (cursor.moveToNext()) {
                    result = cursor.getLong(cursor.getColumnIndex(DocumentsContract.Document.COLUMN_SIZE))
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
        val msg = CustomException.getThrowableResultWithFeedback {
            context.contentResolver.query(uri, arrayOf("_id", DocumentsContract.Document.COLUMN_LAST_MODIFIED),
                null, null, null)?.use { cursor ->
                while (cursor.moveToNext()) {
                    result = cursor.getLong(cursor.getColumnIndex(DocumentsContract.Document.COLUMN_LAST_MODIFIED)).div(1000)
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
            val filename = to.split("/").last()
            val newUri = DocumentsContract.renameDocument(context.contentResolver, uri, filename)
            result = PathUriHelper.getPathFromUri(context, newUri!!)
            if(result != null){
                succeed = true
            }
            succeed
        }
        return ApiResult(succeed, result, msg)
    }

    override fun move(from: Uri, to: Uri): ApiResult<String?> {
        var succeed = false
        var result: String? = null
        val msg = CustomException.getThrowableResultWithFeedback {
            val toDirUri = DocumentsContract.buildDocumentUriUsingTree(
                to,
                DocumentsContract.getTreeDocumentId(to)
            )
            val newUri: Uri = DocumentsContract.moveDocument(context.contentResolver, from, from, toDirUri)!!
            result = PathUriHelper.getPathFromUri(context, newUri)
            if(result != null){
                succeed = true
            }
            succeed
        }
        return ApiResult(succeed, result, msg)
    }
//    override fun createFileInternal(path: String, data: String?): MutableMap<String, Any?> {
//        val createResults = mutableMapOf<String, Any?>()
//        createResults["path"] = CustomException.getCustomExceptionMessage("NOT_SUPPORTED")
//        createResults["action"] = getActionResult(createResults.values.joinToString())
//        return createResults
//    }
//
//    override fun readFileInternal(path: String): MutableMap<String, Any?> {
//        val readResults = mutableMapOf<String, Any?>()
//        readResults["path"] = CustomException.getCustomExceptionMessage("NOT_SUPPORTED")
//        readResults["action"] = getActionResult(readResults.values.joinToString())
//        return readResults
//    }
//
//    override fun deleteFileInternal(path: String): MutableMap<String, Any?> {
//        if (getUriApi == null) {
//            throw Exception("Get Uri Api Combo Pair Not Found")
//        }
//        val deleteResults = mutableMapOf<String, Any?>()
//        val deleted = CustomException.getThrowableResultWithFeedback {
//            val (uri, message) = getUriApi.getUriForExistingFile(path)
//            if (uri == null) {
//                message
//            } else {
//                val result = PathUriHelper.getPathFromUri(context, uri)
//                DocumentsContract.deleteDocument(context.contentResolver, uri)
//                result
//            }
//        }
//        deleteResults["action"] = getActionResult(deleted)
//        return deleteResults
//    }
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
//                try {
//                    val fromUri = getUriApi.getUriForExistingFile(File(from).parentFile.absolutePath).uri
//                    val toUri = getUriApi.getUriForNewFile(to!!).uri
//
//
//                    val sourceFileUri = DocumentsContract.buildDocumentUriUsingTree(
//                        sourceFolderUri,
//                        DocumentsContract.getDocumentId(sourceFile)
//                    )
//                    val toFolderUri = DocumentsContract.buildDocumentUriUsingTree(
//                        uriReturn,
//                        DocumentsContract.getTreeDocumentId(uriReturn)
//                    )
//                    Log.d("StorageFuzzer", "dest $uriReturn and $toFolderUri")
//                    if(toFolderUri != null && sourceFileUri != null && sourceFolderUri != null) {
//                        Log.d("StorageFuzzer", "toFolderUri $toFolderUri sourceFileUri $sourceFileUri sourceFolderUri $sourceFolderUri")
//                        val newUri = DocumentsContract.moveDocument(
//                            context.contentResolver,
//                            sourceFileUri,
//                            sourceFolderUri,
//                            toFolderUri
//                        )
//                        // after moving, we return the feedbacks
//                        if(newUri!=null){
//                            updateResults["path"] = getPathFromUri(context, newUri)
//                        }
//                    }
//
//
//
//                    // 移动文档
//                    val resultUri =
//                        DocumentsContract.moveDocument(context.contentResolver, fromUri, toUri, null)
//
//                    // 检查结果
//                    if (resultUri != null) {
//                        Log.i("Document moved to: $resultUri")
//                    } else {
//                        Log.e("Document move failed")
//                    }
//                } catch (e: FileNotFoundException) {
//                    e.printStackTrace()
//                }
//            }
//        }
//        updateResults["action"] = getActionResult(updateResults.values.joinToString())
//        return updateResults
//    }
//
//    private fun writeContentByUri(uri: Uri, data: String) {
//        context.contentResolver.openOutputStream(uri, "w")?.use { outputStream ->
//            outputStream.write(
//                if (data.startsWith("Base64:")) {
//                    Base64.decode(data.substring(7), Base64.DEFAULT)
//                } else {
//                    data.toByteArray()
//                }
//            )
//        }
//    }
//
//    private fun readContentByUri(uri: Uri): String {
//        var result = ""
//        context.contentResolver.openInputStream(uri)?.use { inputStream ->
//            val readData = inputStream.readBytes()
//            result = if (!isAsciiPrintable(readData)) {
//                "Base64:" + Base64.encodeToString(readData, Base64.DEFAULT)
//            } else {
//                readData.toString(Charset.defaultCharset())
//            }
//        }
//        return result
//    }

}