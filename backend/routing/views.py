from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .clients import http
from .clients.geocoding import NominatimGeocoder
from .clients.routing import OsrmRouter
from .clients.weather import OpenMeteoWeather
from .serializers import PlanRequestSerializer


@api_view(['GET'])
def health(request):
    return Response({'status': 'ok'})


class PlanRouteView(APIView):
    """POST /api/v1/routes/plan - plan up to 3 weather-annotated routes."""

    def post(self, request):
        serializer = PlanRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with http.build_http_client() as client:
            result = services.plan_routes(
                serializer.to_request(),
                geocoder=NominatimGeocoder(client),
                router=OsrmRouter(client),
                weather=OpenMeteoWeather(client),
            )
        return Response(result)
