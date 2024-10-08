import string


class PathTemplate:
    def __init__(self, target_path: string.Template, target):
        self.target_path = target_path
        self.target = target

    def render(self, pname):
        if "{p}_" in self.target_path.template:
            pname = pname.split(".")[-1]
        return self.target_path.substitute(p=pname)
