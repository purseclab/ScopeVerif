package com.abc.storage_verifier.uri_api.get_uri_api
import android.content.ContentUris
import android.content.ContentValues
import android.net.Uri
import android.provider.MediaStore
import androidx.appcompat.app.AppCompatActivity
import com.abc.storage_verifier.*
import java.io.File


class MediaStoreApi(context: AppCompatActivity): GetUriApi(context) {
    override fun getUriForNewFile(path: String): ApiResult<Uri?> {
        var succeed = false
        var uri: Uri? = null
        val isDirectory = path.endsWith("/")
        if (isDirectory) {
            throw Exception("NOT_SUPPORTED: MediaStoreApi does not support creating directory")
        }
        val msg: String = CustomException.getThrowableResultWithFeedback {
            val collection = PathUriHelper.getCollectionByPath(path)
            val contentValues = ContentValues().apply {
                put(MediaStore.MediaColumns.DISPLAY_NAME, path.split("/").last())
            }

            uri = context.contentResolver.insert(collection, contentValues)

            if (uri != null) {
                succeed = true
            }
            succeed
        }
        return ApiResult(succeed, uri, msg)
    }

    override fun getUriForExistingFile(path: String): ApiResult<Uri?> {
        var succeed = false
        var uri: Uri? = null
        val isDirectory = path.endsWith("/")
        if (isDirectory) {
            return ApiResult(false, null, CustomException.getCustomExceptionMessage("NOT_SUPPORTED"))
        }
        val msg: String = CustomException.getThrowableResultWithFeedback {
            val collection = PathUriHelper.getCollectionByPath(path)
            val emulatedPath = PathUriHelper.getEmulatedPath(path)
            context.contentResolver.query(collection, arrayOf("_id", "date_modified", "_size"),
                "_data LIKE ?", arrayOf(emulatedPath), null)?.use { cursor ->
                while (cursor.moveToNext()) {
                    val id = cursor.getLong(cursor.getColumnIndexOrThrow("_id"))
                    val contentUri: Uri = ContentUris.withAppendedId(
                        collection,
                        id
                    )
                    uri = contentUri
                    break
                }
            }
            if (uri != null) {
                succeed = true
            }
            succeed
        }
        return ApiResult(succeed, uri, msg)
    }

}
//
//    override fun createFileInternal(
//        path: String,
//        data: String?
//    ): MutableMap<String, Any?>{
//        val createResults = mutableMapOf<String, Any?>()
//        val writeValue = data?:""
//        createResults["path"] = getThrowableResultWithFeedback {
//            val collection = PathUriHelper.getCollectionByPath(path)
//            val contentValues = ContentValues().apply {
//                put(MediaStore.MediaColumns.DISPLAY_NAME, path.split("/").last())
//            }
//            val uri = context.contentResolver.insert(collection, contentValues)
//            uri?.let { innerIt ->
//                writeContentByUri(innerIt, writeValue)
//                PathUriHelper.getPathFromUri(context, innerIt)
//            }
//        }
//        createResults["action"] = getActionResult(createResults.values.joinToString())
//        return createResults
//    }
//
//    override fun readFileInternal(path: String): MutableMap<String, Any?> {
//        val readResults = mutableMapOf<String, Any?>()
//        val read = getThrowableResult {
//            val collection = PathUriHelper.getCollectionByPath(path)
//            val emulatedPath = PathUriHelper.getEmulatedPath(path)
//            context.contentResolver.query(collection, arrayOf("_id", "date_modified", "_size"),
//                "_data LIKE ?", arrayOf(emulatedPath), null)?.use { cursor ->
//
//                var content = getFileNotFoundMessage()
//                while (cursor.moveToNext()) {
//                    readResults["size"] = getThrowableResultWithFeedback {
//                        cursor.getLong(
//                            cursor.getColumnIndexOrThrow("_size")
//                        )
//                    }
//                    readResults["modified_time"] = getThrowableResultWithFeedback {
//                        cursor.getLong(
//                            cursor.getColumnIndexOrThrow("date_modified")
//                        )
//                    }
//                    val id = cursor.getLong(cursor.getColumnIndexOrThrow("_id"))
//                    val contentUri: Uri = ContentUris.withAppendedId(
//                        collection,
//                        id
//                    )
//                    val originalContentUri = MediaStore.setRequireOriginal(contentUri)
//                    content = try {
//                        readContentByUri(originalContentUri)
//                    } catch (e: java.lang.UnsupportedOperationException) {
//                        Log.d("FILE", "Permission denied, location data stripped!")
//                        getThrowableResultWithFeedback { readContentByUri(contentUri) }
//                    }
//                }
//                readResults["content"] = content
//            }
//        }
//        val values = readResults.values.joinToString()
//        if(values.isBlank()){
//            readResults["action"] = getActionResult(read)
//        }else{
//            readResults["action"] = getActionResult(values)
//        }
//        return readResults
//    }
//
//    override fun deleteFileInternal(path: String): MutableMap<String, Any?> {
//        val deleteResults = mutableMapOf<String, Any?>()
//        val deleted = getThrowableResultWithFeedback {
//            val collection = PathUriHelper.getCollectionByPath(path)
//            val emulatedPath = PathUriHelper.getEmulatedPath(path)
//            var result: String? = getFileNotFoundMessage()
//            context.contentResolver.query(collection, arrayOf("_id"),
//                "_data LIKE ?", arrayOf(emulatedPath), null)?.use{ cursor ->
//                while (cursor.moveToNext()) {
//                    val id = cursor.getLong(cursor.getColumnIndexOrThrow("_id"))
//                    val contentUri: Uri = ContentUris.withAppendedId(
//                        collection,
//                        id
//                    )
//                    result = PathUriHelper.getPathFromUri(context, contentUri)
//                    context.contentResolver.delete(contentUri, null)
//                }
//            }
//            result
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
//        val collection = PathUriHelper.getCollectionByPath(from)
//        val emulatedFrom = PathUriHelper.getEmulatedPath(from)
//        val updateResults = mutableMapOf<String, Any?>()
//        updateResults["path"] = getThrowableResultWithFeedback {
//            // For when updating file content but not file name
//            var nonNullTo = getFileNotFoundMessage()
//            context.contentResolver.query(collection, arrayOf("_id"),
//                "_data LIKE ?", arrayOf(emulatedFrom), null)?.use{ cursor ->
//                while (cursor.moveToNext()) {
//                    nonNullTo = to ?: from
//                    val id = cursor.getLong(cursor.getColumnIndexOrThrow("_id"))
//                    val contentUri: Uri = ContentUris.withAppendedId(
//                        collection,
//                        id
//                    )
//                    // file content update
//                    if (data != null) {
//                        writeContentByUri(contentUri, data)
//                    }
//                    if (from != to && to != null) {
//                        val newValues = ContentValues().apply {
//                            put("_data", nonNullTo)
//                            // rename the file if necessary
//                            if(File(from).name != File(to).name){
//                                put("_display_name", File(to).name)
//                            }
//                        }
//                        context.contentResolver.update(
//                            contentUri,
//                            newValues,
//                            null,
//                            null
//                        )
//
//                        // MediaStore itself cannot be used to move a file
//                        // So we use other internal methods to do the task
//                        if(data != null){
//                            createFileInternal(to, data)
//                            deleteFileInternal(from)
//                        }
//                    }
//                }
//            }
//            nonNullTo
//        }
//        updateResults["action"] = getActionResult(updateResults.values.joinToString())
//        return updateResults
//    }
