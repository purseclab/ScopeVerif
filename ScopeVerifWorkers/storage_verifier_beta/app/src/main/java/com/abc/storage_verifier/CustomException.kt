package com.abc.storage_verifier

import androidx.activity.result.ActivityResult

class CustomException(val msg: String): Exception(msg) {
    companion object {
        fun getExceptionMessage(e: Exception): String {
            return getCustomExceptionMessage(e.stackTraceToString().substring(0, 1000))
        }

        fun getThrowableResult(f: () -> Unit): String {
            return try {
                f()
                "SUCCESS"
            } catch (e: Exception) {
                getExceptionMessage(e)
            }
        }

        fun getThrowableResultWithFeedback(f: () -> Any?): String {
            return try {
                val itemResult = f()
                itemResult?.toString() ?: "UNKNOWN FAILURE"
            } catch (e: Exception) {
                getExceptionMessage(e)
            }
        }

        fun getCustomExceptionMessage(msg: String): String {
            return "EXCEPTION: $msg"
        }

        fun getFileNotFoundMessage(): String {
            return getCustomExceptionMessage("File not found")
        }

        fun hasFalseContent(msg: String): Boolean {
            return msg.contains("\"content\": \"false\"")
        }

        fun hasException(msg: String): Boolean {
            val lowerMsg = msg.lowercase()
            return lowerMsg.contains("exception") || lowerMsg.contains("error")
        }

        fun getActivityFailureMessage(
            it: ActivityResult,
            result: MutableMap<String, Any?>,
            path: String
        ): String {
            return getCustomExceptionMessage("target=${path}, resultCode=${it.resultCode}, data=${it.data}")
        }
    }
}