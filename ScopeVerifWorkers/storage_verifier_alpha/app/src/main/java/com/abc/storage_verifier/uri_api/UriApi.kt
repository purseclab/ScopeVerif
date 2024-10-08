package com.abc.storage_verifier.uri_api

import android.annotation.SuppressLint
import android.net.Uri
import android.util.Log
import androidx.appcompat.app.AppCompatActivity
import com.abc.storage_verifier.*
import com.abc.storage_verifier.PathUriHelper.Companion.getFolderPath
import com.abc.storage_verifier.uri_api.access_uri_api.FileDescriptorApi
import com.abc.storage_verifier.uri_api.access_uri_api.IOStreamApi
import com.abc.storage_verifier.uri_api.get_uri_api.MediaStoreApi
import com.abc.storage_verifier.uri_api.get_uri_api.SafPickerApi
import com.abc.storage_verifier.uri_api.manage_uri_api.ContentResolverApi
import com.abc.storage_verifier.uri_api.manage_uri_api.DocumentFileApi
import com.abc.storage_verifier.uri_api.manage_uri_api.DocumentsContractApi
import java.io.File


fun getUriApi(context: AppCompatActivity, apiList: List<String>, action: String, target: String): UriApi {
    val getUriApiName = apiList[0]
    val manageUriApiName = apiList[1]
    val accessUriApiName = apiList[2]

    val getUriApi: GetUriApi = when (getUriApiName) {
        "media-store" -> MediaStoreApi(context)
        "saf-picker" -> SafPickerApi(context)
        else -> throw Exception("Unknown Get Uri API: $getUriApiName")
    }
    Log.d("StorageFuzzer", "GetUriApi $getUriApi")

    val manageUriApi: ManageUriApi = when (manageUriApiName) {
        "content-resolver" -> ContentResolverApi(context)
        "documents-contract" -> DocumentsContractApi(context)
        "document-file" -> DocumentFileApi(context)
        else -> throw Exception("Unknown Manage Uri API: $manageUriApiName")
    }
    val accessUriApi: AccessUriApi = when (accessUriApiName) {
        "file-descriptor" -> FileDescriptorApi(context)
        "io-stream" -> IOStreamApi(context)
        else -> throw Exception("Unknown Access Uri API: $accessUriApiName")
    }
    return UriApi(context, action, target, getUriApi, manageUriApi, accessUriApi)
}

class UriApi(context: AppCompatActivity, tag: String, target: String, getUriApi: GetUriApi,
             manageUriApi: ManageUriApi, accessUriApi: AccessUriApi): AbstractUriStorageApi(context, tag, target, getUriApi, manageUriApi, accessUriApi) {
    private fun moveWithUri(succeed: Boolean, toDir: Uri?, msg: String, from: Uri?) {
        val moveResults = mutableMapOf<String, Any?>()
        if (!succeed || toDir == null || from == null) {
            moveResults["edit_path"] = msg
            returnFeedback(evaluateResult(moveResults.values), moveResults)
            return
        }
        val (moveSucceed, newPath, moveMessage) =  manageUriApi.move(from, toDir)
        if (!moveSucceed){
            moveResults["edit_path"] = moveMessage
            returnFeedback(evaluateResult(moveResults.values),moveResults)
            return
        }
        moveResults["edit_path"] = newPath
        returnFeedback(evaluateResult(moveResults.values),moveResults)
        return
    }

    private fun renameByUri(getUriSucceed:Boolean, uri: Uri?, getUriMessage: String?, useless: String?, to: String? = null){
        Log.d("StorageFuzzer", "renameByUri $getUriSucceed $uri $getUriMessage")
        val renameResults = mutableMapOf<String, Any?>()
        if (!getUriSucceed || uri == null) {
            renameResults["edit_path"] = getUriMessage
            returnFeedback(evaluateResult(renameResults.values), renameResults)
            return
        }
        if (to == null) {
            throw Exception("to is null")
        }

        val (renameSucceed, newPath, renameMessage) = manageUriApi.rename(uri, to)
        if (!renameSucceed){
            renameResults["edit_path"] = renameMessage
            returnFeedback(evaluateResult(renameResults.values), renameResults)
            return
        }
        renameResults["edit_path"] = newPath
        returnFeedback(evaluateResult(renameResults.values), renameResults)
        return
    }

    private fun readByUri(getUriSucceed:Boolean, uri: Uri?, getUriMessage: String?, useless: String? = null, useless2: String? = null){
        Log.d("StorageFuzzer", "readByUri $getUriSucceed $uri $getUriMessage")
        val readResults = mutableMapOf<String, Any?>()
        if (!getUriSucceed || uri == null) {
            readResults["content"] = getUriMessage
            returnFeedback(evaluateResult(readResults.values), readResults)
            return
        }

        // prevent Android 14 redirect the read
        val path = PathUriHelper.getPathFromUri(context, uri)
        readResults["path"] = path

        val (readContentSucceed, content, readContentMessage) = accessUriApi.read(uri)
        if (!readContentSucceed || content == null) {
            readResults["content"] = readContentMessage
        }else{
            readResults["content"] = content
        }

        val (getSizeSucceed, size, getSizeMessage) = manageUriApi.getSize(uri)
        if (!getSizeSucceed || size == null) {
            readResults["size"] = getSizeMessage
        }else{
            readResults["size"] = size
        }


        val (getModifiedTimeSucceed, modifiedTime, getModifiedTimeMessage) = manageUriApi.getModifiedTime(uri)
        if (!getModifiedTimeSucceed || modifiedTime == null) {
            readResults["modified_time"] = getModifiedTimeMessage
        }else{
            readResults["modified_time"] = modifiedTime
        }
        returnFeedback(evaluateResult(readResults.values), readResults)
        return
    }

    private fun writeByUri(getUriSucceed:Boolean, uri: Uri?, getUriMessage: String?, data: String?, useless: String? = null){
        Log.d("StorageFuzzer", "createByUri $getUriSucceed $uri $getUriMessage")
        val createResults = mutableMapOf<String, Any?>()
        if (!getUriSucceed || uri == null) {
            createResults["edit_path"] = getUriMessage
            returnFeedback(evaluateResult(createResults.values), createResults)
            return
        }

        val (createSucceed, newPath, createMessage) = accessUriApi.write(uri, data ?: "")
        if (!createSucceed || newPath == null) {
            createResults["edit_path"] = createMessage
            returnFeedback(evaluateResult(createResults.values), createResults)
            return
        }

        createResults["edit_path"] = newPath
        returnFeedback(evaluateResult(createResults.values), createResults)
        return
    }

    private fun deleteByUri(getUriSucceed:Boolean, uri: Uri?, getUriMessage: String?, useless: String? = null, useless2: String? = null){
        Log.d("StorageFuzzer", "deleteByUri $getUriSucceed $uri $getUriMessage")
        val deleteResults = mutableMapOf<String, Any?>()
        if(!getUriSucceed || uri == null) {
            deleteResults["edit_path"] = "false"
            returnFeedback(evaluateResult(getUriMessage!!), deleteResults)
            return
        }

        val (deleteSucceed, newPath, deleteMessage) = manageUriApi.delete(uri)
        if (!deleteSucceed) {
            deleteResults["edit_path"] = "false"
            returnFeedback(evaluateResult(deleteMessage!!), deleteResults)
            return
        }
        deleteResults["edit_path"] = newPath
        returnFeedback(evaluateResult(deleteMessage!!), deleteResults)
        return
    }

    override fun readFile(path: String){
        if(getUriApi is SafPickerApi){
            getUriApi.getUriForExistingFile(path, null, null, ::readByUri)
        }else{
            val (getUriSucceed, uri, getUriMessage) = getUriApi.getUriForExistingFile(path)
            readByUri(getUriSucceed, uri, getUriMessage)
        }
    }

    override fun createFile(path: String, data: String?){
        if(getUriApi is SafPickerApi){
            getUriApi.getUriForNewFile(path, data, ::writeByUri)
        }else{
            val (getUriSucceed, uri, getUriMessage) = getUriApi.getUriForNewFile(path)
            writeByUri(getUriSucceed, uri, getUriMessage, data)
        }
    }

    override fun deleteFile(path: String){
        if(getUriApi is SafPickerApi){
            getUriApi.getUriForExistingFile(path, null, null, ::deleteByUri)
        }else{
            val (getUriSucceed, uri, getUriMessage) = getUriApi.getUriForExistingFile(path)
            deleteByUri(getUriSucceed, uri, getUriMessage)
        }
    }

    override fun renameFile(from: String, to: String){
        if(getUriApi is SafPickerApi){
            getUriApi.getUriForExistingFile(from, to, null, ::renameByUri)
        }else{
            val (getUriSucceed, uri, getUriMessage) = getUriApi.getUriForExistingFile(from)
            renameByUri(getUriSucceed, uri, getUriMessage, null, to)
        }
    }

    override fun moveFile(from: String, to: String) {
        if(getUriApi is SafPickerApi){
            getUriApi.getUrisForMovingFile(from, to, ::moveWithUri)
        }else{
            val moveResults = mutableMapOf<String, Any?>()
            val (getUriSucceed, uri, getUriMessage) = getUriApi.getUriForExistingFile(from)
            if (!getUriSucceed || uri == null) {
                moveResults["edit_path"] = getUriMessage
                returnFeedback(evaluateResult(moveResults.values), moveResults)
                return
            }
            // MediaStore cannot move file to a new folder
            // so we need to create a new file, and then move the content
            val toFile = File(to, File(from).name).absolutePath
            val (getToUriSucceed, toUri, getToUriMessage) = getUriApi.getUriForNewFile(toFile)
            if (!getToUriSucceed || toUri == null) {
                moveResults["edit_path"] = getToUriMessage
                returnFeedback(evaluateResult(moveResults.values), moveResults)
                return
            }

            val (moveSucceed, newPath, moveMessage) = manageUriApi.move(uri, toUri)
            if (!moveSucceed){
                moveResults["edit_path"] = moveMessage
                returnFeedback(evaluateResult(moveResults.values), moveResults)
                return
            }

            if(newPath!=null){
                val realFolderPath = getFolderPath(PathUriHelper.getEmulatedPath(newPath))
                val folderPath = getFolderPath(PathUriHelper.getEmulatedPath(to))
                if(realFolderPath != folderPath){
                    moveResults["edit_path"] = "false"
                    returnFeedback(evaluateResult(moveResults.values), moveResults)
                    return
                }
            }

            moveResults["edit_path"] = newPath
            returnFeedback(evaluateResult(moveResults.values), moveResults)
            return
        }
    }

    override fun overwriteFile(from: String, data: String) {
        if (File(from).exists()){
            if(getUriApi is SafPickerApi){
                getUriApi.getUriForExistingFile(from, null, data, ::writeByUri)
            }else{
                val (getUriSucceed, uri, getUriMessage) = getUriApi.getUriForExistingFile(from)
                writeByUri(getUriSucceed, uri, getUriMessage, data)
            }
        }else{
            throw Exception("File not exists")
        }
    }
}