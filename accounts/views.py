from django.contrib.auth import login
from django.urls import reverse_lazy
from django.views.generic import CreateView
from .forms import CustomCreationForm


class SignUpView(CreateView):
    form_class = CustomCreationForm
    template_name = 'accounts/signup.html'
    success_url = reverse_lazy('job_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        # Log the new user in straight away
        login(self.request, self.object)
        return response
