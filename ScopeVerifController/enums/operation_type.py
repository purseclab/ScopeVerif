import enum
from enums.operation_variable import OperationVariable


class OperationType(enum.Enum):
    def __repr__(self):
        return self.value["type"]

    READ = {
        "type": "READ_FILE",
        "flag": "READ_FILE",
        "perm_modified": set(),
        "default_param": {
            "path": OperationVariable.ALPHA_PATH,
        }
    }
    CREATE = {
        "type": "CREATE_FILE",
        "flag": "CREATE_FILE",
        "perm_modified": set(),
        "default_param": {
            "path": OperationVariable.ALPHA_PATH,
            "data": OperationVariable.ALPHA_DATA
        }
    }

    DELETE = {
        "type": "DELETE_FILE",
        "flag": "DELETE_FILE",
        "perm_modified": set(),
        "default_param": {
            "path": OperationVariable.ALPHA_PATH
        }
    }

    MOVE = {
        "type": "MOVE_FILE",
        "flag": "MOVE_FILE",
        "perm_modified": {},
        "default_param": {
            "path": OperationVariable.ALPHA_PATH,
            "move_to": OperationVariable.BETA_DIRPATH,
        }
    }

    RENAME = {
        "type": "RENAME_FILE",
        "flag": "RENAME_FILE",
        "perm_modified": {},
        "default_param": {
            "path": OperationVariable.ALPHA_PATH,
            "move_to": OperationVariable.ALPHA_PATH2
        }
    }

    OVERWRITE = {
        "type": "OVERWRITE_FILE",
        "flag": "OVERWRITE_FILE",
        "perm_modified": {},
        "default_param": {
            "path": OperationVariable.ALPHA_PATH,
            "data": OperationVariable.ALPHA_DATA2
        }
    }

