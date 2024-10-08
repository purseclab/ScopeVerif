from enums.app_permission import AppPermission


class PermissionSetting:
    ks = [AppPermission.ACCESS_MEDIA_LOCATION,
          AppPermission.READ_EXTERNAL_STORAGE,
          AppPermission.MANAGE_EXTERNAL_STORAGE,
          AppPermission.WRITE_EXTERNAL_STORAGE,
          AppPermission.WRITE_MEDIA_STORAGE]

    def __init__(self, data=None):
        self.data = {p: False for p in AppPermission}
        if data is not None:
            self.data = data

    def is_granted(self, perm):
        return self.data.get(perm, False)

    def enable(self, perm):
        self.data[perm] = True

    def disable(self, perm):
        self.data[perm] = False

    @staticmethod
    def from_array(arr):
        obj = PermissionSetting()
        for i in range(len(obj.ks)):
            obj.data[obj.ks[i]] = bool(arr[i])
        return obj

    def to_array(self):
        return [int(self.data[self.ks[i]]) for i in range(len(self.ks))]

    def to_printable(self):
        printable = {}
        for k in self.ks:
            printable[k.value] = self.data[k]
        return printable
