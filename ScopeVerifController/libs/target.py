import string
from typing import Union, List
from enums.target_enum import Storage, Collection, Scope, All


class Target:
    def __init__(self, storage: Union[Storage, All] = All,
                 collection: Union[Collection, All] = All,
                 scope: Union[Scope, All] = All):
        self.storage = storage
        self.collection = collection
        self.scope = scope

    def __repr__(self):
        return f"{self.storage.name}-{self.collection.name}-{self.scope.name}"

    def get_paths(self) -> List[string.Template]:
        paths = []
        for storage in self.storage.value:
            for collection in self.collection.value:
                path = storage
                if self.storage != Storage.INTERNAL_STORAGE:
                    path += collection
                if set(self.collection.value).issubset(set(
                        All([Collection.SHARED_IMAGE, Collection.SHARED_AUDIO,
                             Collection.SHARED_VIDEO, Collection.SHARED_DOWNLOAD]).value)):
                    path = string.Template(path+"/${p}_")
                else:
                    path = string.Template(path+"/${p}/")
                paths.append(path)
        return sorted(paths, key=lambda x: x.template)
