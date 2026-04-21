from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter

from .models import Equipment, MonitorPoint, CollectionInterface
from .serializers import (
    EquipmentListSerializer,
    EquipmentDetailSerializer,
    MonitorPointSerializer,
    MonitorPointCreateSerializer,
    CollectionInterfaceSerializer,
)


class EquipmentViewSet(viewsets.ModelViewSet):
    queryset = Equipment.objects.all()
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['status']
    search_fields = ['name', 'code', 'location']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return EquipmentDetailSerializer
        return EquipmentListSerializer

    @action(detail=True, methods=['get'])
    def monitor_points(self, request, pk=None):
        equipment = self.get_object()
        points = equipment.monitor_points.all()
        serializer = MonitorPointSerializer(points, many=True)
        return Response(serializer.data)


class MonitorPointViewSet(viewsets.ModelViewSet):
    queryset = MonitorPoint.objects.select_related('equipment', 'threshold').all()
    permission_classes = [AllowAny]

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return MonitorPointCreateSerializer
        return MonitorPointSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        equipment_id = self.request.query_params.get('equipment_id')
        if equipment_id:
            qs = qs.filter(equipment_id=equipment_id)
        return qs

    @action(detail=True, methods=['get', 'post', 'put', 'delete'], url_path='collection')
    def collection(self, request, pk=None):
        point = self.get_object()

        if request.method == 'GET':
            try:
                serializer = CollectionInterfaceSerializer(point.collection)
                return Response(serializer.data)
            except CollectionInterface.DoesNotExist:
                return Response(status=status.HTTP_204_NO_CONTENT)

        if request.method == 'DELETE':
            try:
                point.collection.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            except CollectionInterface.DoesNotExist:
                return Response(status=status.HTTP_404_NOT_FOUND)

        # POST (create) or PUT (update) — upsert logic
        try:
            instance = point.collection
            serializer = CollectionInterfaceSerializer(instance, data=request.data)
        except CollectionInterface.DoesNotExist:
            serializer = CollectionInterfaceSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)
        serializer.save(monitor_point=point)
        return Response(serializer.data)
