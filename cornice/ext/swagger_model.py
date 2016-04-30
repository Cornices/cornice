import colander


class SwaggerModel(object):

    def __init__(self):
        self.mappings = {
            colander.Mapping: self._swagger_mapping,
            colander.Sequence: self._swagger_sequence,
            colander.Tuple: self._swagger_tuple,
            colander.DateTime: self._swagger_datetime,
            colander.Integer: self._swagger_integer,
            colander.Float: self._swagger_number,
            colander.String: self._swagger_string,
            colander.Money: self._swagger_number,
            colander.Boolean: self._swagger_boolean,
            colander.Decimal: self._swagger_number,
            colander.Date: self._swagger_date,
            colander.Time: self._swagger_time,
        }
        self.models = {}

    def add_model(self, model):
        _model = {model["name"]: {
            "type": model["type"],
            "properties": model[model["name"]],
            "required": [x["name"]
                         for x in model[model["name"]].values()
                         if "required" in x and x["required"]]
        }}
        self.models.update(_model)
        return {"$ref": "#/definitions/%s" % model["name"]}

    def to_swagger(self, node):
        if hasattr(node, "location") and node.location != "body":
            return None
        nodetype = type(node.typ)
        converter = self.mappings.get(nodetype)
        ret = converter(node)
        title = node.title or node.__class__.__name__
        ret["name"] = title
        if node.description:
            ret["description"] = node.description
        if node.default != colander.null:
            ret["default"] = node.default
        if ret.get("type", "") == "object":
            return self.add_model(ret)
        else:
            ret["name"] = title.lower()
        return ret

    def _swagger_mapping(self, node):
        ret = {}
        title = node.title or node.__class__.__name__
        ret["type"] = "object"
        ret["required"] = node.required
        props = {}
        ret[title] = props
        for cnode in node.children:
            name = cnode.name
            tmp = self.to_swagger(cnode)
            if tmp:
                props[name] = tmp
        return ret

    def _swagger_sequence(self, node):
        ret = {}
        ret["required"] = node.required
        tmp = self.to_swagger(node.children[0])
        if not tmp:
            return ret
        items = tmp
        ret["schema"] = {"items": items}
        ret["schema"]["type"] = "array"

        for v in self._node_validators(node):
            if isinstance(v, colander.Length):
                if v.min is not None:
                    ret["schema"]["minItems"] = v.min
                if v.max is not None:
                    ret["schema"]["maxItems"] = v.max
        return ret

    def _swagger_tuple(self, node):
        ret = {}
        ret["required"] = node.required
        items = []
        ret["schema"] = {"items": items}
        ret["schema"]["type"] = "array"
        for cnode in node.children:
            tmp = self.to_swagger(cnode)
            if tmp:
                items.append(tmp)
        return ret

    def _swagger_datetime(self, node, format="date-time"):
        ret = {}
        ret["type"] = "string"
        ret["required"] = node.required
        ret["format"] = format
        return ret

    def _swagger_date(self, node):
        return self._swagger_datetime(node, format="date")

    def _swagger_time(self, node):
        return self._swagger_datetime(node, format="time")

    def _swagger_string(self, node):
        ret = {}
        ret["type"] = "string"
        ret["required"] = node.required

        for v in self._node_validators(node):
            if isinstance(v, colander.Length):
                if v.min is not None:
                    ret["minLength"] = v.min
                if v.max is not None:
                    ret["maxLength"] = v.max
            elif isinstance(v, colander.OneOf):
                ret["enum"] = v.choices
        return ret

    def _swagger_number(self, node, typename="number"):
        ret = {}
        ret["type"] = typename
        ret["required"] = node.required

        for v in self._node_validators(node):
            if isinstance(v, colander.Range):
                if v.max is not None:
                    ret["maximum"] = v.max
                if v.min is not None:
                    ret["minimum"] = v.min
            elif isinstance(v, colander.OneOf):
                ret["enum"] = v.choices
        return ret

    def _swagger_boolean(self, node):
        ret = {}
        ret["type"] = "boolean"
        ret["required"] = node.required
        return ret

    def _swagger_integer(self, node):
        return self._swagger_number(node, typename="integer")

    def _node_validators(self, node):
        ret = []
        if node.validator is not None:
            if isinstance(node.validator, colander.All):
                ret = node.validator.validators
            else:
                ret.append(node.validator)
        return ret
