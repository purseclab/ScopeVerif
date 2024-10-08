package com.abc.storage_verifier

import android.os.Bundle
import android.util.Log
import androidx.appcompat.app.AppCompatActivity
import com.abc.storage_verifier.path_api.FileApi
import com.abc.storage_verifier.uri_api.getUriApi

const val READ_TAG = "READ_FILE"
const val CREATE_TAG = "CREATE_FILE"
const val DELETE_TAG = "DELETE_FILE"
const val MOVE_TAG = "MOVE_FILE"
const val RENAME_TAG = "RENAME_FILE"
const val OVERWRITE_TAG = "OVERWRITE_FILE"


class OperationActivity: AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // init app-specific folder in external storage
        getExternalFilesDir(null)
        Log.d("FILE", intent.action.toString())

        // initialize API
        val action = intent.action.toString()
        val apiName = intent.getStringExtra("api") ?: throw Exception("Unknown API: null")
        val target = intent.getStringExtra("path")!!
        val apiList = apiName.split("@")
        val api: AbstractStorageApi = when (apiList.size) {
            1 -> {
                val pathApi = apiList[0]
                when (pathApi) {
                    "file" -> FileApi(this, action, target)
                    else -> throw Exception("Unknown Path API: $pathApi")
                }
            }
            3 -> {
                getUriApi(this, apiList, action, target)
            }
            else -> {
                throw Exception("API combinations not supported: $apiList")
            }
        }
        Log.d("StorageFuzzer", "api $api")

        Log.d("FILE", "tag: $action")
        try{
            when (action) {
                CREATE_TAG -> {
                    val path = intent.getStringExtra("path")!!
                    val data =
                        if (intent.hasExtra("data")) intent.getStringExtra("data") else null
                    api.createFile(path, data)
                }
                DELETE_TAG -> {
                    val path = intent.getStringExtra("path")!!
                    api.deleteFile(path)
                }
                RENAME_TAG -> {
                    val from = intent.getStringExtra("path")!!
                    val to = intent.getStringExtra("move_to")!!
                    api.renameFile(from, to)
                }
                MOVE_TAG -> {
                    val from = intent.getStringExtra("path")!!
                    val to = intent.getStringExtra("move_to")!!
                    if(!to.endsWith("/")){
                        throw Exception("Please use directory path as move_to")
                    }
                    api.moveFile(from, to)
                }
                OVERWRITE_TAG -> {
                    val from = intent.getStringExtra("path")!!
                    val data = intent.getStringExtra("data")!!
                    api.overwriteFile(from, data)
                }
                READ_TAG -> {
                    val path = intent.getStringExtra("path")!!
                    api.readFile(path)
                }
                else -> throw Exception("Unknown FLAG")
            }
        }catch (e: Exception){
            val errorMsg = CustomException.getExceptionMessage(e)
            api.returnFeedback(errorMsg, mutableMapOf())
        }
    }
}