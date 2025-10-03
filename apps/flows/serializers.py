from rest_framework import serializers
from .models import Flow, Node, Path, Entity, EntityValue

class EntityValueSerializer(serializers.ModelSerializer):
    class Meta:
        model = EntityValue
        fields = ['id', 'entity', 'team', 'sender_id', 'value']

class EntitySerializer(serializers.ModelSerializer):
    values = EntityValueSerializer(many=True, read_only=True)

    class Meta:
        model = Entity
        fields = ['id', 'name', 'slug', 'type', 'options', 'team', 'values']


class PathSerializer(serializers.ModelSerializer):
    class Meta:
        model = Path
        fields = "__all__"

class NodeSerializer(serializers.ModelSerializer):
    paths = PathSerializer(many=True, read_only=True)

    class Meta:
        model = Node
        fields = "__all__"

class FlowSerializer(serializers.ModelSerializer):
    nodes = NodeSerializer(many=True, read_only=True)

    class Meta:
        model = Flow
        fields = "__all__"


#----

class PathSimpleSerializer(serializers.ModelSerializer):
    target_node_id = serializers.IntegerField(source="target_node.id", read_only=True)

    class Meta:
        model = Path
        fields = ["id", "condition", "target_node_id"]


class NodeSimpleSerializer(serializers.ModelSerializer):
    paths = PathSimpleSerializer(many=True, read_only=True)
    collect_entity = serializers.StringRelatedField()
    default_path_id = serializers.IntegerField(source="default_path.id", read_only=True)

    class Meta:
        model = Node
        fields = [
            "id",
            "type", 
            "message_template",
            "collect_entity",
            "paths",
            "default_path_id", 
        ]


class FlowDetailSerializer(serializers.ModelSerializer):
    nodes = NodeSimpleSerializer(many=True, read_only=True)

    class Meta:
        model = Flow
        fields = [
            "id",
            "name",
            "nodes",
        ]
