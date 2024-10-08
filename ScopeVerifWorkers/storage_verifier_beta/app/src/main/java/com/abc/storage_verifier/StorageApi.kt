package com.abc.storage_verifier
import android.net.Uri
import android.util.Log
import androidx.appcompat.app.AppCompatActivity
import org.json.JSONObject

interface StorageApiInterface {
    // "readFile" will return a feedback contains all attributes except "path" (it is a parameter)
    // "createFile" and "updateFile" only return a feedback contains "success" and "path", other attributes are direct/indirect parameters. the "path" of the updated file may be given by the System (auto-rename), so it can be considered as a "feedback"
    // "deleteFile" only return a feedback contains "success"
    fun readFile(path: String)
    fun createFile(path: String, data: String?)
    fun deleteFile(path: String)
    fun moveFile(from: String, to: String)
    fun renameFile(from: String, to: String)
    fun overwriteFile(from: String, data: String)
}

abstract class AbstractStorageApi(val context: AppCompatActivity, val action: String, val target: String): StorageApiInterface{
    override fun readFile(path: String) {throw Exception("NOT_IMPLEMENTED")}

    override fun createFile(path: String, data: String?) {throw Exception("NOT_IMPLEMENTED")}

    override fun deleteFile(path: String) {throw Exception("NOT  _IMPLEMENTED")}
    override fun moveFile(from: String, to: String){throw Exception("NOT_IMPLEMENTED")}
    override fun renameFile(from: String, to: String){throw Exception("NOT_IMPLEMENTED")}
    override fun overwriteFile(from: String, data: String){throw Exception("NOT_IMPLEMENTED")}

    fun returnFeedback(success: String, result: MutableMap<String, Any?>){
        // for result, map true/false/null to string, others keep the same
        val mappedResults = mutableMapOf<String, Any?>()
        for((key, value) in result){
            when(value){
                true -> mappedResults[key] = "true"
                false -> mappedResults[key] = "false"
                null -> mappedResults[key] = "null"
                else -> mappedResults[key] = value
            }
        }
        val feedback = mutableMapOf("target" to target, "action" to action, "success" to success, "result" to mappedResults)
        (feedback as Map<*, *>?)?.let { JSONObject(it).toString(4) }?.let { Log.d(action, it) }
        context.finish()
    }
    protected fun evaluateResult(msg: Any): String {
        if(msg is Collection<*> && msg.isNotEmpty()){
            val exceptions = msg.filter {CustomException.hasException(it.toString())}
            val nonFalse = msg.filter {it.toString() != "false"}
            return if (exceptions.isNotEmpty()){
                exceptions.joinToString("\n")
            }else if(nonFalse.isEmpty()) {
                "FAIL"
            }else{
                "SUCCESS"
            }
        }else if(msg is String) {
            return if (CustomException.hasException(msg)) {
                msg
            }else if (msg == "success" || msg == "true") {
                "SUCCESS"
            }else {
                "FAIL"
            }
        }else if(msg is Boolean){
            return if(msg){
                "SUCCESS"
            }else{
                "FAIL"
            }
        }else{
            return "UNKNOWN"
        }
    }

}

abstract class AbstractUriStorageApi(context: AppCompatActivity,
                                     action: String,
                                     target: String,
                                     val getUriApi: GetUriApi,
                                     val manageUriApi: ManageUriApi,
                                     val accessUriApi: AccessUriApi): AbstractStorageApi(context, action, target)
data class ApiResult<T>(val succeed: Boolean, val result: T, val message: String?)

abstract class GetUriApi(val context: AppCompatActivity) {
    open fun getUriForExistingFile(path: String): ApiResult<Uri?> {throw Exception("NOT_IMPLEMENTED")}
    open fun getUriForNewFile(path: String): ApiResult<Uri?> {throw Exception("NOT_IMPLEMENTED")}
}

abstract class ManageUriApi(val context: AppCompatActivity) {
    open fun delete(uri: Uri): ApiResult<String?> {throw Exception("NOT_IMPLEMENTED")}
    open fun getSize(uri: Uri): ApiResult<Long?> {throw Exception("NOT_IMPLEMENTED")}
    open fun getModifiedTime(uri: Uri): ApiResult<Long?> {throw Exception("NOT_IMPLEMENTED")}
    open fun rename(uri: Uri, to: String): ApiResult<String?> {throw Exception("NOT_IMPLEMENTED")}
    open fun move(from: Uri, to: Uri): ApiResult<String?> {throw Exception("NOT_IMPLEMENTED")}
}

abstract class AccessUriApi(val context: AppCompatActivity) {
    open fun read(uri: Uri): ApiResult<String?> {throw Exception("NOT_IMPLEMENTED")}
    open fun write(uri: Uri, content: String): ApiResult<String?> {throw Exception("NOT_IMPLEMENTED")}
}

fun isPlaintext(input: ByteArray): Boolean {
    if (input.size < 100) return true
    for(element in input) {
        if (element !in 32..126) return false
    }
    return true
}