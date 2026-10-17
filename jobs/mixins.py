from functools import wraps

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect


class RoleRequiredMixin(LoginRequiredMixin):
    """Allow access only to logged-in users with the given role."""
    required_role = None
    role_message = "You don't have permission to access that page."

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if request.user.role != self.required_role:
            messages.error(request, self.role_message)
            return redirect('job_list')
        return super().dispatch(request, *args, **kwargs)


class EmployerRequiredMixin(RoleRequiredMixin):
    required_role = 'employer'
    role_message = "Only employer accounts can manage job postings."


class SeekerRequiredMixin(RoleRequiredMixin):
    required_role = 'seeker'
    role_message = "Only job seeker accounts can apply to jobs."


def role_required(role, message):
    """Function-view version of RoleRequiredMixin. Use after @login_required."""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if request.user.role != role:
                messages.error(request, message)
                return redirect('job_list')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


seeker_required = role_required('seeker', SeekerRequiredMixin.role_message)
employer_required = role_required('employer', EmployerRequiredMixin.role_message)
