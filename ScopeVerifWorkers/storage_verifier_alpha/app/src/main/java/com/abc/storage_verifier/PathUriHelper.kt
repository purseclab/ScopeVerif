package com.abc.storage_verifier

import android.annotation.SuppressLint
import android.content.ContentUris
import android.content.Context
import android.database.Cursor
import android.net.Uri
import android.os.Environment
import android.provider.DocumentsContract
import android.provider.MediaStore
import android.util.Log
import android.webkit.MimeTypeMap


class PathUriHelper {
    companion object{
        private const val DOC_AUTHORITY = "com.android.externalstorage.documents"

        @SuppressLint("SdCardPath")
        fun getFolderPath(path: String): String {
            var folderPath = if(path.startsWith("/sdcard/Android")){
                path.substringAfter("/sdcard")
            }else{
                path.substringAfter("/sdcard/")
            }
            if(!path.endsWith("/")){
                folderPath = folderPath.substring(0, folderPath.lastIndexOf("/"))
            }
            return folderPath
        }

        @SuppressLint("SdCardPath")
        fun getCollectionByPath(path: String): Uri {
            val convertPath = if (path.contains("/sdcard/")) {
                getEmulatedPath(path)
            } else {
                path
            }

            if(!convertPath.contains("/storage/emulated/0/") || convertPath.contains("/Android/data")){
                throw Exception("MediaStore API is not supported for this path: $convertPath")
            }
            val collection = when(convertPath.split("/")[4]){
                "Download" -> MediaStore.Downloads.EXTERNAL_CONTENT_URI
                "Pictures" -> MediaStore.Images.Media.EXTERNAL_CONTENT_URI
                "Movies" -> MediaStore.Video.Media.EXTERNAL_CONTENT_URI
                "Music" -> MediaStore.Audio.Media.EXTERNAL_CONTENT_URI
                else -> throw Exception("MediaStore API is not supported for this path!")
            }
            return collection
        }

        // Get /storage/emulated/0 path
        fun getEmulatedPath(path: String): String {
            return if (path.contains("/storage/emulated/0/")) {
                path
            } else if(!path.contains("/storage/emulated/0/") && path.contains("/sdcard/")) {
                path.replace("sdcard", "storage/emulated/0")
            } else {
                throw Exception("MediaStore API is not supported for this path!")
            }
        }

        // StackOverflow: https://stackoverflow.com/questions/17546101/get-real-path-for-uri-android/61995806#61995806
        @SuppressLint("SdCardPath")
        fun getPathFromUri(context: Context, uri: Uri): String? {
            // DocumentProvider
            if (DocumentsContract.isDocumentUri(context, uri)) {
                Log.d("StorageVerifier", "isDocumentUri: ${uri}")
                // ExternalStorageProvider
                if (isExternalStorageDocument(uri)) {
                    val docId = DocumentsContract.getDocumentId(uri)
                    val split = docId.split(":").toTypedArray()
                    val type = split[0]
                    if ("primary".equals(type, ignoreCase = true)) {
                        return Environment.getExternalStorageDirectory().toString() + "/" + split[1]
                    }

                    // TODO handle non-primary volumes
                } else if (isDownloadsDocument(uri)) {
                    Log.d("StorageVerifier", "isDownloadsDocument: ${uri}")
                    val id = DocumentsContract.getDocumentId(uri)
                    val contentUri: Uri = ContentUris.withAppendedId(
                        Uri.parse("content://downloads/public_downloads"), java.lang.Long.valueOf(id)
                    )
                    val data = try{
                        getDataColumn(context, contentUri, null, null)
                    }catch (e: java.lang.IllegalArgumentException){
                        getDataColumn(context, uri, null, null)
                    }
                    if(data==null) return data
                    if (data.startsWith("/storage/emulated")) {
                        return data
                    }
                    return getEmulatedPath("/sdcard/Download/${data}")
                } else if (isMediaDocument(uri)) {
                    Log.d("StorageVerifier", "isMediaDocument: ${uri}")
                    val docId = DocumentsContract.getDocumentId(uri)
                    val split = docId.split(":").toTypedArray()
                    val type = split[0]
                    var contentUri: Uri? = null
                    if ("image" == type) {
                        contentUri = MediaStore.Images.Media.EXTERNAL_CONTENT_URI
                    } else if ("video" == type) {
                        contentUri = MediaStore.Video.Media.EXTERNAL_CONTENT_URI
                    } else if ("audio" == type) {
                        contentUri = MediaStore.Audio.Media.EXTERNAL_CONTENT_URI
                    }
                    val selection = "_id=?"
                    val selectionArgs = arrayOf(
                        split[1]
                    )
                    return getDataColumn(context, contentUri, selection, selectionArgs)
                }
            } else if ("content".equals(uri.getScheme(), ignoreCase = true)) {
                Log.d("StorageVerifier", "remote: ${uri}")
                // Return the remote address
                return if (isGooglePhotosUri(uri)) uri.getLastPathSegment() else getDataColumn(
                    context,
                    uri,
                    null,
                    null
                )
            } else if ("file".equals(uri.getScheme(), ignoreCase = true)) {
                return uri.getPath()
            }
            return null
        }

        private fun getDataColumn(
            context: Context, uri: Uri?, selection: String?,
            selectionArgs: Array<String>?
        ): String? {
            var cursor: Cursor? = null
            val column = "_data"
            val projection = arrayOf(
                column,
                "_display_name"
            )
            try {
                cursor = uri?.let {
                    context.contentResolver.query(
                        it, projection, selection, selectionArgs,
                        null
                    )
                }
                if (cursor != null && cursor.moveToFirst()) {
                    val index: Int = cursor.getColumnIndexOrThrow(column)
                    val index2: Int = cursor.getColumnIndexOrThrow("_display_name")
                    val str1 = cursor.getString(index)
                    val str2 = cursor.getString(index2)
                    return if(str1 != null){
                        str1
                    } else {
                        Log.d("StorageVerifier", "Used displayName: ${str2}")
                        str2
                    }
                }
            } finally {
                if (cursor != null) cursor.close()
            }
            return null
        }


        /**
         * @param uri The Uri to check.
         * @return Whether the Uri authority is ExternalStorageProvider.
         */
        private fun isExternalStorageDocument(uri: Uri): Boolean {
            return "com.android.externalstorage.documents" == uri.getAuthority()
        }

        /**
         * @param uri The Uri to check.
         * @return Whether the Uri authority is DownloadsProvider.
         */
        private fun isDownloadsDocument(uri: Uri): Boolean {
            return "com.android.providers.downloads.documents" == uri.getAuthority()
        }

        /**
         * @param uri The Uri to check.
         * @return Whether the Uri authority is MediaProvider.
         */
        private fun isMediaDocument(uri: Uri): Boolean {
            return "com.android.providers.media.documents" == uri.getAuthority()
        }

        /**
         * @param uri The Uri to check.
         * @return Whether the Uri authority is Google Photos.
         */
        private fun isGooglePhotosUri(uri: Uri): Boolean {
            return "com.google.android.apps.photos.content" == uri.getAuthority()
        }

        // Source: https://github.com/folderv/androidDataWithoutRootAPI33/blob/main/app/src/main/java/com/android/test/DocumentVM.kt
        fun getFolderUri(id: String?, tree: Boolean): Uri {
            return if (tree) DocumentsContract.buildTreeDocumentUri(DOC_AUTHORITY, id) else DocumentsContract.buildDocumentUri(DOC_AUTHORITY, id)
        }

        fun getOriginalUri(contentUri: Uri): Uri {
            return MediaStore.setRequireOriginal(contentUri)
        }

        fun getMimeTypeByPath(path: String): String {
            val extension = MimeTypeMap.getFileExtensionFromUrl(path)
            return MimeTypeMap.getSingleton().getMimeTypeFromExtension(extension) ?: "plain/text"
        }
    }
}