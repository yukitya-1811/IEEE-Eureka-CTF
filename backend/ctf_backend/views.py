from django.shortcuts import render
from django_nextjs.render import render_nextjs_page_sync
# from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework import viewsets
from .models import Team, Question, Flagresponse
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from .serialisers import TeamsSerializer, QuestionsSerializer, FlagresponsesSerializer, ScoreboardSerializer
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from rest_framework.decorators import api_view
# from django.contrib.auth import authenticate, login
from datetime import datetime, tzinfo
from django.utils.timezone import make_aware
from rest_framework.decorators import action
from django.http import JsonResponse
from django.contrib.auth import logout
from celery import shared_task
from rest_framework.decorators import api_view, permission_classes
from .middleware import TimeRestrictedMiddleware
import pytz

def index(request):
    return render_nextjs_page_sync(request)

class TeamsViewSet(viewsets.ModelViewSet):
    queryset = Team.objects.all()
    serializer_class = TeamsSerializer
    # permission_classes = [IsAuthenticated]
    def create(self,request): # Basically to handle POST Requests
        return Response("Nope",status=status.HTTP_404_NOT_FOUND)
    @action(detail=True, methods=['GET'])
    def team_detail(self, request, pk=None):
        team = self.get_object()  # Get the team instance
        serializer = self.get_serializer(team)  # Serialize the team data
        return Response(serializer.data)

class QuestionsViewSet(viewsets.ModelViewSet):
    queryset = Question.objects.all()
    serializer_class = QuestionsSerializer
    permission_classes = [IsAuthenticated]
    def create(self,request): # Basically to handle POST Requests
        return Response("Nope",status=status.HTTP_404_NOT_FOUND)
    def list(self, request): # Basically to handle GET Requests
        # astimezone(tz=pytz.timezone('Asia/Kolkata'))
        current_time = make_aware(datetime.now())
        slot1 = make_aware(datetime(2023, 11, 17, 19, 0, 0))
        slot2 = make_aware(datetime(2023, 11, 18, 0, 3, 0))
        slot3 = make_aware(datetime(2023, 11, 18, 3, 0, 0))
        slot4 = make_aware(datetime(2023, 11, 18, 6, 0, 0))
        slot5 = make_aware(datetime(2023, 11, 18, 9, 0, 0))
        if current_time >= slot1 and current_time < slot2:
            questions = Question.objects.filter(id__range=(1, 15))
        elif current_time >= slot2 and current_time < slot3:
            questions = Question.objects.filter(id__range=(1, 21))
        elif current_time >= slot3 and current_time < slot4:
            questions = Question.objects.filter(id__range=(1, 26))
        elif current_time >= slot4 and current_time < slot5:
            questions = Question.objects.filter(id__range=(1, 30))
        elif current_time >= slot5:
            questions = Question.objects.filter(id__range=(1, 33))
        else:
            questions = Question.objects.none()
        serializer = self.get_serializer(questions,many=True)
        return Response(serializer.data)

class FlagresponsesViewSet(viewsets.ModelViewSet):
    queryset = Flagresponse.objects.all()
    serializer_class = FlagresponsesSerializer
    permission_classes = [IsAuthenticated]
    def create(self, request):
        if request.method == "POST":
            flagres = request.data.get('flag')
            qnid = request.data.get('id')
            timestamp = make_aware(datetime.now())
            print('entered')
            try:
                question = get_object_or_404(Question, id=qnid)
                if flagres != question.flag:
                    raise ValidationError("Flag is incorrect")
            except ValidationError as e:
                return Response({'error': "Flag Incorrect"}, status=status.HTTP_400_BAD_REQUEST)
            user = request.user
            existing_flag_response = Flagresponse.objects.filter(team__user=user, question=question)
            if existing_flag_response.exists():
                return Response({'error': "You have already submitted a response for this question."}, status=status.HTTP_404_NOT_FOUND)

            data = {
                'team': user.team.id,
                'question': question.id,
                'response': flagres,
                'timestamp': timestamp,
            }
            # serializer = FlagresponsesSerializer(data=data)
            # if serializer.is_valid():
            Flagresponse.objects.create(team=user.team,timestamp=timestamp,question=question,response=flagres)
            return Response({"Done"},status=status.HTTP_200_OK)
                # serializer.save()
                # return Response(serializer.data, status=status.HTTP_201_CREATED)
            # else:
                # return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ScoreboardViewSet(viewsets.ModelViewSet):
    queryset = Team.objects.all()
    serializer_class = ScoreboardSerializer
    permission_classes = [IsAuthenticated]
    def create(self,request): # Basically to handle POST Requests
        return Response("Nope",status=status.HTTP_404_NOT_FOUND)
    def list(self, request):
        user = request.user
        teams = Team.objects.all()
        scores = []
        for team in teams:
            responses = Flagresponse.objects.filter(team=team)
            total_score = sum(response.question.points for response in responses)
            scores.append(total_score)
        if user.team in teams:
            responses = Flagresponse.objects.filter(team=user.team)
            current_user_score = sum(response.question.points for response in responses)
        scores.sort(reverse=True)
        top_10_scores = scores[:10]
        serialized_data = ScoreboardSerializer({'top_10_scores': top_10_scores, 'current_user_score': current_user_score})
        return Response(serialized_data.data)
    
@api_view(['POST'])
@permission_classes([IsAuthenticated])  # Add this line
def custom_logout(request):
    logout(request)
    return JsonResponse({'message': 'Logged out successfully'})

import json
import jwt
from django.views.decorators.csrf import csrf_exempt
@csrf_exempt
def verify_token(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            token = data.get('token')
            
            # Replace 'your_secret_key' with the actual secret key used to sign the JWT
            secret_key = 'django-insecure-ah&w004!i7v0ia6l4n_bi73k%t^orf=*a6ygl59-pyfh7-3zu7'
            
            try:
                # Attempt to decode and verify the JWT
                decoded_token = jwt.decode(token, secret_key, algorithms=['HS256'])
                return JsonResponse({'message': 'Token is valid', 'decoded_token': decoded_token})
            except jwt.ExpiredSignatureError:
                return JsonResponse({'message': 'Token has expired'}, status=403)
            except jwt.DecodeError:
                return JsonResponse({'message': 'Token is invalid'}, status=403)

        except json.JSONDecodeError:
            return JsonResponse({'message': 'Invalid JSON data'}, status=400)

    else:
        return JsonResponse({'message': 'Invalid request method'}, status=405)