package com.abc.storage_verifier.uri_api.get_uri_api

import android.app.Activity
import android.content.Intent
import android.net.Uri
import android.provider.DocumentsContract
import android.util.Log
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import com.abc.storage_verifier.*
import com.abc.storage_verifier.PathUriHelper.Companion.getEmulatedPath
import com.abc.storage_verifier.PathUriHelper.Companion.getFolderPath
import com.abc.storage_verifier.PathUriHelper.Companion.getFolderUri

class SafPickerApi(context: AppCompatActivity): GetUriApi(context) {
    fun getUriForExistingFile(path: String, to: String?, content: String?,
                              callback: (succeed: Boolean, uri: Uri?, msg: String, content: String?, to: String?) -> Unit){
        var succeed = false
        var uri: Uri? = null
        // determine if path is a file or a directory
        val isDirectory = path.endsWith("/")
        if(isDirectory) {
            throw Exception("getUriForExistingFile: path is not a file")

        }
        val getResult =
            context.registerForActivityResult(
                ActivityResultContracts.StartActivityForResult()
            ) {
                if (it.resultCode == Activity.RESULT_OK) {
                    uri = it.data?.data
                    if(uri!=null){
                        // real path of fromUri
                        val realPath = PathUriHelper.getPathFromUri(context, uri!!)
                        if(realPath!=null){
                            val realFolderPath = getFolderPath(getEmulatedPath(realPath))
                            val folderPath = getFolderPath(getEmulatedPath(path))
                            if(realFolderPath == folderPath){
                                succeed = true
                            }else{
                                Log.d("StorageVerifier", "Path Redirected: real path $realFolderPath, from $folderPath")
                            }
                        }
                    }else{
                        Log.d("StorageVerifier", "Uri not found")
                    }
                }
                callback(succeed, uri, succeed.toString(), content, to)
            }

        val folderPath = getFolderPath(path)
        // Send file name to accessibility service
        val filename = path.split("/").last()
        Log.d("StorageVerifier", "sending file to accessibility: $filename")
        val intent = getSafIntent(Intent.ACTION_OPEN_DOCUMENT, folderPath, path.split("/").last())
        getResult.launch(intent)
    }

    fun getUrisForMovingFile(from: String, to: String,
                             callback: (succeed: Boolean, uri: Uri?, msg: String, from: Uri?) -> Unit){
        var succeed = false
        var fromUri: Uri? = null
        var toUri: Uri? = null
        // determine if path is a file or a directory
        val isDirectory = to.endsWith("/")
        if(!isDirectory) {
            throw Exception("getUrisForFileAndFolder: to is not a directory")
        }
        val getToResult =
            context.registerForActivityResult(
                ActivityResultContracts.StartActivityForResult()
            ) {
                if (it.resultCode == Activity.RESULT_OK) {
                    toUri = it.data?.data
                    if(toUri!=null){
                        succeed = true
                    }
                }
                callback(succeed, toUri, succeed.toString(), fromUri)
            }
        val getFromResult =
            context.registerForActivityResult(
                ActivityResultContracts.StartActivityForResult()
            ) {
                if (it.resultCode == Activity.RESULT_OK) {
                    fromUri = it.data?.data
                    if(fromUri!=null){
                        // real path of fromUri
                        val realPath = PathUriHelper.getPathFromUri(context, fromUri!!)
                        if(realPath!=null && getFolderPath(getEmulatedPath(realPath))==getFolderPath(
                                getEmulatedPath(from))) {
                            succeed = true
                        }else{
                            Log.d("StorageVerifier", "Path Redirected: real path $realPath, from $from")
                        }
                    }
                }
                if(!succeed){
                    callback(false, fromUri, false.toString(), null)
                }else{
                    Log.d("SafApi", "getUrisForMovingFile: $to")
                    val intent = getSafIntent(Intent.ACTION_OPEN_DOCUMENT_TREE, getFolderPath(to))
                    // pass the uri of the file to be moved to the next activity
                    getToResult.launch(intent)
                }
            }
        // Send file name to accessibility service
        val filename = from.split("/").last()
        val folderPath = getFolderPath(from)
        getFromResult.launch(getSafIntent(Intent.ACTION_OPEN_DOCUMENT, folderPath, filename))
    }

    fun getUriForNewFile(path: String, content: String?, callback: (succeed: Boolean, uri: Uri?, msg: String, content: String?) -> Unit){
        var succeed = false
        var uri: Uri? = null
        // determine if path is a file or a directory
        val isDirectory = path.endsWith("/")

        val getResult =
            context.registerForActivityResult(
                ActivityResultContracts.StartActivityForResult()
            ) {
                if (it.resultCode == Activity.RESULT_OK) {
                    uri = it.data?.data
                    if(uri!=null){
                        // real path of fromUri
                        val realPath = PathUriHelper.getPathFromUri(context, uri!!)
                        if(realPath!=null && getFolderPath(getEmulatedPath(realPath))==getFolderPath(
                                getEmulatedPath(path))) {
                            succeed = true
                        }else{
                            Log.d("StorageVerifier", "Path Redirected: real path $realPath, from $path")
                        }
                    }
                }
                callback(succeed, uri, succeed.toString(), content)
            }

        val folderPath = getFolderPath(path)

        val intent = if(!isDirectory) {
            Log.d("SafApi", "getUriForNewFile: $folderPath, ${path.split("/").last()}")
            getSafIntent(Intent.ACTION_CREATE_DOCUMENT, folderPath, path.split("/").last())
        }else{
            Log.d("SafApi", "getUriForNewFile: $folderPath")
            getSafIntent(Intent.ACTION_OPEN_DOCUMENT_TREE, folderPath)

        }
        getResult.launch(intent)
    }

    private fun getSafIntent(action: String, folderPath: String, createdFile: String? = null): Intent{
        return Intent(action).apply {
            if(action!=Intent.ACTION_OPEN_DOCUMENT_TREE) {
                type = "*/*"
                addCategory(Intent.CATEGORY_OPENABLE)
            }
            if(createdFile!=null) putExtra(Intent.EXTRA_TITLE, createdFile)
            putExtra(DocumentsContract.EXTRA_INITIAL_URI, getFolderUri("primary:$folderPath", false))
        }
    }
//
//    // the SAF API need to return the results in internal methods
//    override fun readFile(path: String) {
//        readFileInternal(path)
//    }
//
//    override fun deleteFile(path: String) {
//        deleteFileInternal(path)
//    }
//
//    override fun createFile(path: String, data: String?) {
//        createFileInternal(path, data)
//    }
//
//    override fun updateFile(from: String, to: String?, data: String?) {
//        updateFileInternal(from, to, data)
//    }
//
//    override fun readFileInternal(path: String): MutableMap<String, Any?> {
//        val feedbacks: MutableMap<String, Any?> = mutableMapOf()
//        var readResults: MutableMap<String, Any?> = mutableMapOf()
//
//        val getResult =
//            context.registerForActivityResult(
//                ActivityResultContracts.StartActivityForResult()
//            ) {
//                if (it.resultCode == Activity.RESULT_OK) {
//                    val uriReturn = it.data?.data
//                    if (uriReturn != null) {
//                        readResults = readFileByUrl(uriReturn, readResults)
//                        readResults["action"] = getActionResult(readResults.values.joinToString())
//                    }
//                }
//                if (!readResults.contains("action")) {
//                    // read failed
//                    readResults["action"] = getActivityFailureMessage(it, readResults, path)
//                }
//                feedbacks[READ_TAG] = readResults
//                returnFeedback(feedbacks)
//            }
//
//        // Send file name to accessibility service
//        val filename = path.split("/").last()
//        dataToAccessibility(SELECT_ACC_SERVICE, filename)
//
//        val folderPath = getFolderPath(path)
//        val intent = getSafIntent(Intent.ACTION_OPEN_DOCUMENT, folderPath)
//        getResult.launch(intent)
//        return mutableMapOf()
//    }
//
//    override fun createFileInternal(path: String, data: String?): MutableMap<String, Any?> {
//        val feedbacks: MutableMap<String, Any?> = mutableMapOf()
//        val createResults: MutableMap<String, Any?> = mutableMapOf()
//
//        val getResult =
//            context.registerForActivityResult(
//                ActivityResultContracts.StartActivityForResult()
//            ) {
//                if (it.resultCode == Activity.RESULT_OK) {
//                    val uriReturn = it.data?.data
//                    if (uriReturn != null) {
//                        val writeValue = data ?: ""
//                        createResults["path"] = getThrowableResultWithFeedback {
//                            writeContentByUri(uriReturn, writeValue)
//                            getPathFromUri(context, uriReturn)
//                        }
//                        createResults["action"] =
//                            getActionResult(createResults.values.joinToString())
//                    }
//                }
//                if (!createResults.contains("action")) {
//                    // read failed
//                    createResults["action"] = getActivityFailureMessage(it, createResults, path)
//                }
//                feedbacks[CREATE_TAG] = createResults
//                returnFeedback(feedbacks)
//            }
//
//        val folderPath = getFolderPath(path)
//        val intent = getSafIntent(Intent.ACTION_CREATE_DOCUMENT, folderPath, path.split("/").last())
//        getResult.launch(intent)
//        return mutableMapOf()
//    }
//
//    override fun deleteFileInternal(path: String): MutableMap<String, Any?> {
//        val feedbacks: MutableMap<String, Any?> = mutableMapOf()
//        val deleteResults: MutableMap<String, Any?> = mutableMapOf()
//
//        // Run when SAF returns
//        val getResult =
//            context.registerForActivityResult(
//                ActivityResultContracts.StartActivityForResult()
//            ) {
//                Log.d("FILE", "STARTED")
//                if (it.resultCode == Activity.RESULT_OK) {
//                    val uriReturn = it.data?.data
//                    if (uriReturn != null) {
//                        val deleted = getThrowableResult {
//                            DocumentFile.fromSingleUri(context, uriReturn)?.delete()
//                        }
//                        deleteResults["action"] = getActionResult(deleted)
//                    }
//                }
//                if (!deleteResults.contains("action")) {
//                    // read failed
//                    deleteResults["action"] = getActivityFailureMessage(it, deleteResults, path)
//                }
//                feedbacks[DELETE_TAG] = deleteResults
//                returnFeedback(feedbacks)
//            }
//
//        // Send file name to accessibility service
//        val filename = path.split("/").last()
//        dataToAccessibility(SELECT_ACC_SERVICE, filename)
//
//        val folderPath = getFolderPath(path)
//        val intent = getSafIntent(Intent.ACTION_OPEN_DOCUMENT, folderPath)
//        getResult.launch(intent)
//
//        return mutableMapOf()
//    }
//
//    override fun updateFileInternal(
//        from: String,
//        to: String?,
//        data: String?
//    ): MutableMap<String, Any?> {
//        val feedbacks: MutableMap<String, Any?> = mutableMapOf()
//        val updateResults: MutableMap<String, Any?> = mutableMapOf()
//        val intermediateValues: MutableMap<String, Any?> = mutableMapOf()
//        var activeLauncher = 0
//
//        fun attemptToReturnFeedbacks(result:ActivityResult, path:String){
//            if(activeLauncher==0){
//                if (!updateResults.contains("action")) {
//                    // something failed
//                    updateResults["action"] = getActivityFailureMessage(result, updateResults, path)
//                }
//                updateResults["action"] = getActionResult(updateResults.values.joinToString())
//                feedbacks[UPDATE_TAG] = updateResults
//                returnFeedback(feedbacks)
//            }else{
//                Log.d(UPDATE_TAG, "there are $activeLauncher launchers still active, cannot return the feedbacks")
//            }
//        }
//
//        // define folder picker to get URI of the target folder
//        val destFolderPicker = context.registerForActivityResult(
//            ActivityResultContracts.StartActivityForResult()
//        ) {
//            if (it.resultCode == Activity.RESULT_OK) {
//                val sourceFile = if(intermediateValues.contains("sourceFile")) intermediateValues["sourceFile"] as Uri else null
//                val sourceFolderUri = if(intermediateValues.contains("sourceFolder")) intermediateValues["sourceFolder"] as Uri else null
//                val uriReturn = it.data?.data
//                if (uriReturn != null){
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
//                }
//            }
//            activeLauncher --
//            attemptToReturnFeedbacks(it, to?:from)
//        }
//
//        // define folder picker to the source folder
//        val sourceFolderPicker = context.registerForActivityResult(
//            ActivityResultContracts.StartActivityForResult()
//        ) {
//            if (it.resultCode == Activity.RESULT_OK) {
//                val uriReturn = it.data?.data
//                if (uriReturn != null) {
//                    val parentFolderUri = DocumentsContract.buildDocumentUriUsingTree(
//                        uriReturn,
//                        DocumentsContract.getTreeDocumentId(uriReturn)
//                    )
//                    Log.d("StorageFuzzer", "source $uriReturn and $parentFolderUri")
//                    intermediateValues["sourceFolder"] = parentFolderUri
//                    val intent = getSafIntent(Intent.ACTION_OPEN_DOCUMENT_TREE, getFolderPath(to!!))
//                    destFolderPicker.also{activeLauncher++}.launch(intent)
//                }
//            }
//            activeLauncher --
//            attemptToReturnFeedbacks(it, to?:from)
//        }
//
//        // define file picker to get URI of the source file
//        val sourceFilePicker = context.registerForActivityResult(
//            ActivityResultContracts.StartActivityForResult()
//        ) {
//            if (it.resultCode == Activity.RESULT_OK) {
//                var uriReturn = it.data?.data
//                if (uriReturn != null) {
//                    // 1. data overwrite if necessary
//                    if (data != null) {
//                        writeContentByUri(uriReturn, data)
//                    }
//                    // 2. rename the file if necessary
//                    if (to != null && File(from).name != File(to).name) {
//                        val newUri = DocumentsContract.renameDocument(context.contentResolver, uriReturn, File(to).name)
//                        if(newUri!=null) uriReturn = newUri
//                    }
//                    // 3. move a file if necessary
//                    if (to != null && (File(from).parentFile != File(to).parentFile)) {
//                        intermediateValues["sourceFile"] = uriReturn
//                        val intent = getSafIntent(Intent.ACTION_OPEN_DOCUMENT_TREE, getFolderPath(from))
//                        sourceFolderPicker.also{activeLauncher++}.launch(intent)
//                    }else{
//                        // if file moving is not required, we return results here
//                        updateResults["path"] = getThrowableResultWithFeedback{getPathFromUri(context, uriReturn)}
//                    }
//                }
//            }
//            activeLauncher --
//            attemptToReturnFeedbacks(it, to?:from)
//        }
//
//        // First, we send "from" file name to accessibility service
//        val filename = from.split("/").last()
//        dataToAccessibility(SELECT_ACC_SERVICE, filename)
//        // and launch the source file picker
//        val fromFolderPath: String = getFolderPath(from)
//        val intent = getSafIntent(Intent.ACTION_OPEN_DOCUMENT, fromFolderPath)
//        sourceFilePicker.also{activeLauncher++}.launch(intent)
//        return mutableMapOf()
//    }
//
//    private fun readFileByUrl(uri: Uri, result: MutableMap<String, Any?>): MutableMap<String, Any?> {
//        context.contentResolver.query(uri, null, null, null, null)?.use { cursor ->
//            while (cursor.moveToNext()) {
//                result["modified_time"] = getThrowableResultWithFeedback { cursor.getLong(cursor.getColumnIndexOrThrow("last_modified"))/1000 }
//                result["size"] = getThrowableResultWithFeedback { cursor.getLong(cursor.getColumnIndexOrThrow(OpenableColumns.SIZE)) }
//                result["content"] = getThrowableResultWithFeedback{  readContentByUri(uri) }
//            }
//        }
//        return result
//    }
//
//    private fun dataToAccessibility(action: String, filename: String) {
//        val broadcastIntent = Intent()
//        broadcastIntent.action = action
//        broadcastIntent.putExtra("filename", filename)
//        context.sendBroadcast(broadcastIntent)
//    }
//

//

}

