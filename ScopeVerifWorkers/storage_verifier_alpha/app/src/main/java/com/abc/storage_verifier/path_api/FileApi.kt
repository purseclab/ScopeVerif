package com.abc.storage_verifier.path_api

import android.util.Base64
import androidx.appcompat.app.AppCompatActivity
import com.abc.storage_verifier.*
import java.io.File
import java.nio.charset.Charset

class FileApi(context: AppCompatActivity, tag: String, target: String): AbstractStorageApi(context, tag, target) {
    override fun readFile(path: String){
        val file = File(path)
        val readResults = mutableMapOf<String, Any?>()
        readResults["content"] = CustomException.getThrowableResultWithFeedback {
            val contentBytes = file.readBytes()
            var content = ""
            if (!isPlaintext(contentBytes)) {
                content = "Base64:" + Base64.encodeToString(contentBytes, Base64.DEFAULT)
            } else {
                content = contentBytes.toString(Charset.defaultCharset())
            }
            content
        }
        readResults["size"] = CustomException.getThrowableResultWithFeedback {
            file.length()
        }
        readResults["modified_time"] = CustomException.getThrowableResultWithFeedback {
            file.lastModified()/1000
        }
        returnFeedback(evaluateResult(readResults.values), readResults)
    }

    override fun createFile(path: String, data: String?){
        val file = File(path)
        val createResults: MutableMap<String, Any?> = mutableMapOf()
        createResults["edit_path"] = CustomException.getThrowableResultWithFeedback {
            // if string starts with "Base64:", then it should be writes as bytes
            if (data != null) {
                if (data.startsWith("Base64:")) {
                    file.writeBytes(Base64.decode(data.substring(7), Base64.DEFAULT))
                } else {
                    file.writeText(data)
                }
            }else{
                file.createNewFile()
            }
            file.absolutePath
        }
        returnFeedback(evaluateResult(createResults.values), createResults)
    }

    override fun deleteFile(path: String){
        val file = File(path)
        var deleted = false
        val deleteResults = mutableMapOf<String, Any?>()
        CustomException.getThrowableResult{
            file.delete()
            deleted = !file.exists()
        }
        if(deleted){
            deleteResults["edit_path"] = path
        }else{
            deleteResults["edit_path"] = "false"
        }
        returnFeedback(evaluateResult(deleted), deleteResults)
    }

    override fun moveFile(from: String, to: String) {
        val fromFile = File(from)
        val toDirFile = File(to)
        val toFile = File(toDirFile, fromFile.name)
        if(fromFile.parent == toFile.parent){
            throw Exception("Please use renameFile if you just want to rename it")
        }
        val moveResults = mutableMapOf<String, Any?>()
        moveResults["edit_path"] = CustomException.getThrowableResultWithFeedback {
            fromFile.copyTo(toFile, true)
            fromFile.delete()
            toFile.absolutePath
        }
        returnFeedback(evaluateResult(moveResults.values), moveResults)
    }

    override fun renameFile(from: String, to: String) {
        val fromFile = File(from)
        val toFile = File(to)
        if(fromFile.parentFile != toFile.parentFile){
            throw Exception("Cannot rename file to another directory")
        }
        val moveResults = mutableMapOf<String, Any?>()
        moveResults["edit_path"] = CustomException.getThrowableResultWithFeedback {
            val succeed = fromFile.renameTo(toFile)
            if(!succeed){
                throw Exception("Cannot rename file")
            }
            to
        }
        returnFeedback(evaluateResult(moveResults.values), moveResults)
    }

    override fun overwriteFile(from: String, data: String) {
        val fromFile = File(from)
        if (fromFile.exists()) {
            val succeed = CustomException.getThrowableResult {
                // if string starts with "Base64:", then it should be writes as bytes
                if (data.startsWith("Base64:")) {
                    fromFile.writeBytes(Base64.decode(data.substring(7), Base64.DEFAULT))
                } else {
                    fromFile.writeText(data)
                }
            }
            returnFeedback(evaluateResult(succeed), mutableMapOf())
        } else {
            throw Exception("File not exists")
        }
    }
}