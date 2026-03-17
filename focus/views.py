from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required


@login_required
def start_focus_session(request):
    request.session['focus_active'] = True
    return render(request, "focus/start.html")


@login_required
def end_focus_session(request):
    request.session['focus_active'] = False
    return render(request, "focus/end.html")


@login_required
def focus_status(request):
    status = request.session.get('focus_active', False)
    return JsonResponse({"focus_active": status})

from django.shortcuts import get_object_or_404
from django.utils import timezone
from .models import FocusSession

@login_required
def end_session(request, session_id):
    session = get_object_or_404(FocusSession, id=session_id)

    session.end_time = timezone.now()
    session.duration_seconds = int(
        (session.end_time - session.start_time).total_seconds()
    )

    if session.duration_seconds > 300:
        session.completed = True

    session.save()

    return JsonResponse({"status": "ended"})


from django.utils import timezone
from .models import FocusSession

def start_session(request):
    session = FocusSession.objects.create(
        user=request.user,
        start_time=timezone.now()
    )
    return redirect("study_feed")