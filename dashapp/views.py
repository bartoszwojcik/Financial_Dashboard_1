from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.utils.decorators import method_decorator
from guardian.decorators import permission_required_or_403
from guardian.mixins import PermissionRequiredMixin
from django.contrib.auth.models import User, Group
from django.http import request, HttpRequest, Http404, HttpResponseForbidden
from django.shortcuts import render, redirect
from django.template.response import TemplateResponse
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import TemplateView, FormView
from dashapp.forms import LoginForm, UserRegisterForm, CompanyRegisterForm, \
    AddRevenueForm, EmployeeRegisterForm
from dashapp.models import Revenue, Expense, Employee, Customer, Procedure, \
    Country, PaymentType, Project, Currency, ExpenseCategory, Company, \
    CompanyMember
from dashapp.mixins import GroupRequiredMixin
from guardian.shortcuts import assign_perm, get_perms
from datetime import date



# ToDo: Maybe move those functions somewhere else?

def revenue_calculator(company_id, start_date, end_date):
     data = Revenue.objects.filter(
        company=company_id,
        document_date__gte=start_date,
        document_date__lte=end_date
        )
     total = 0
     for revenue in data:
         total += revenue.net_amount_converted
     return total

def expense_calculator(company_id, start_date, end_date):
    data = Expense.objects.filter(
        company=company_id,
        document_date__gte=start_date,
        document_date__lte=end_date
    )
    total = 0
    for revenue in data:
        total += revenue.net_amount
    return total

def receipt_calculator(company_id, start_date, end_date):
    data = Revenue.objects.filter(
        company=company_id,
        settlement_status=True,
        expected_payment_date__gte=start_date,
        expected_payment_date__lte=end_date,
    )
    total = 0
    for receipt in data:
        total += receipt.net_amount
    return total

def expenditure_calculator(company_id, start_date, end_date):
    data = Expense.objects.filter(
        company=company_id,
        settlement_status=True,
        expected_payment_date__gte=start_date,
        expected_payment_date__lte=end_date,
    )
    total = 0
    for expenditure in data:
        total += expenditure.net_amount
    return total


# Views begin here

class HomePageView(TemplateView):
    template_name = "home.html"


class LoginView(FormView):
    template_name = "login.html"
    form_class = LoginForm
    # ToDo: should send user back to main page? Or to the panel perhaps?
    success_url = ""
    # success_url = reverse_lazy("main-dashboard", kwargs=request.user.companymember.company.id)

    def form_valid(self, form):
        user = authenticate(
            username=form.cleaned_data["login"],
            password=form.cleaned_data["password"]
        )
        if user is not None:
            login(self.request, user, backend='django.contrib.auth.backends.ModelBackend')
            self.success_url = reverse_lazy(
                "main-dashboard", kwargs={"pk": user.companymember.company.id}
            )
            return super(LoginView, self).form_valid(form)

        else:
            return self.render_to_response(self.get_context_data(
                form=form,
                error="No user exists with that username."
            )), user

    def form_invalid(self, form):
        return self.render_to_response(self.get_context_data(
                form=form,
                error="Wrong login or password."
            ))

def logout_view(request):
    logout(request)
    return redirect(reverse("home"))


class MainRegistrationView(View):
    def get(self, request):
        return TemplateResponse(
            request, "registration.html", {
                "form_company": CompanyRegisterForm,
                "form_manager": UserRegisterForm
            }
        )

    def post(self, request):
        form_company = CompanyRegisterForm(request.POST)
        form_manager = UserRegisterForm(request.POST)
        if form_company.is_valid() and form_manager.is_valid():

            # Check if passwords match each other
            if form_manager.cleaned_data["password"]\
                != form_manager.cleaned_data["password_repeated"]:
                return TemplateResponse(
                    request, "registration.html", {
                        "form_company": form_company,
                        "form_manager": form_manager,
                        "error": "Passwords do not match."
                    }
                )

            # Create a new company
            new_company = form_company.save()

            # Create a new manager-user
            new_user = User.objects.create_user(
                username=form_manager.cleaned_data["username"],
                password=form_manager.cleaned_data["password"],
                email=form_manager.cleaned_data["email"],
                first_name=form_manager.cleaned_data["first_name"],
                last_name=form_manager.cleaned_data["last_name"],
            )
            CompanyMember.objects.create(
                company=new_company,
                user=new_user
            )

            # Create a new group for this company, using its pk
            # and add permissions to the group
            new_group = Group.objects.create(
                name=("company_" + str(new_company.pk))
            )
            assign_perm("view_company", new_group, new_company)     # ToDo: To jest chyba niepotrzebne


            # Add user to groups
            Group.objects.get(pk=2).user_set.add(new_user)
            # new_user.groups.add(new_group)          # ToDo: To jest chyba niepotrzebne

            login(request, new_user, backend='django.contrib.auth.backends.ModelBackend')
            return redirect(
                reverse("main-dashboard", kwargs={"pk": new_company.id})
            )
        else:
            return TemplateResponse(
            request, "registration.html", {
                "form_company": form_company,
                "form_manager": form_manager
            }
        )


class NewEmployeeRegistrationView(LoginRequiredMixin, View):
    def get(self, request, pk):
        return TemplateResponse(
            request, "employee_registration.html", {
                "form_employee": EmployeeRegisterForm
            }
        )

    def post(self, request, pk):
        form = EmployeeRegisterForm(request.POST)

        if form.is_valid() and form.is_valid():

            # Need to generate a password for user
            password = "temporary"

            # Create a new user
            new_user = User.objects.create_user(
                username=form.cleaned_data["username"],
                password=password,
                email=form.cleaned_data["email"],
                first_name=form.cleaned_data["first_name"],
                last_name=form.cleaned_data["last_name"],
            )

            CompanyMember.objects.create(
                company=Company.objects.get(pk=pk),
                user=new_user
            )

            # Add user to groups
            Group.objects.get(pk=form.cleaned_data["group"]).user_set.add(new_user)

            return redirect(
                reverse("manager-dashboard",
                        kwargs={"pk": pk})
            )
        else:
            return TemplateResponse(
                request, reverse("new-employee", kwargs={"pk": pk}), {
                    "form_employee": form,
                }
        )


# Dashboard views

class MainDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "main_dashboard.html"


    def get_context_data(self, **kwargs):
        year_beginning = date(date.today().year, 1, 1)
        year_end = date(date.today().year, 12, 31)
        month_beginning = date(date.today().year, date.today().month, 1)

        return {
            # ToDo: Tu są bzdury, zmienić gdy będzie funkcja do obliczania
            "current_month_revenue": revenue_calculator(
                self.kwargs["pk"],
                month_beginning,
                year_end
            ),
            "last_month_revenue": revenue_calculator(
                self.kwargs["pk"],
                month_beginning,
                year_end
            ),
            "annual_revenue": revenue_calculator(
                self.kwargs["pk"],
                year_beginning,
                year_end
            ),
        }


class ManagerDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "manager_dashboard.html"

    def get_context_data(self, **kwargs):
        year_beginning = date(date.today().year, 1, 1)
        year_end = date(date.today().year, 12, 31)

        revenues = revenue_calculator(
                self.kwargs["pk"],
                year_beginning,
                year_end
            )
        expenses = expense_calculator(
                self.kwargs["pk"],
                year_beginning,
                year_end
            )
        net = revenues - expenses

        receipts = receipt_calculator(
                self.kwargs["pk"],
                year_beginning,
                year_end
            )

        expenditures = expenditure_calculator(
            self.kwargs["pk"],
            year_beginning,
            year_end
        )

        cash_change = receipts - expenditures

        return {
            "annual_revenue": revenues,
            "annual_expenses": expenses,
            "annual_net": net,
            "annual_receipts": receipts,
            "annual_expenditures": expenditures,
            "annual_cash_change": cash_change
        }

class RevenuesView(LoginRequiredMixin,TemplateView):
    # Tabela mogłaby wyświetlać tylko część danych, a reszta w popupie po naciśnięciu?
    template_name = "revenues.html"

    def get_context_data(self, **kwargs):

        # ToDo: To powinno wyświetlać ileśtam najnowszych + filtry

        return {
            "revenues" : Revenue.objects.filter(
                company=self.kwargs["pk"]
            ).order_by("document_date"),
            "revenue_form": AddRevenueForm
        }

    # Form -> RevenueAddView (jak dla rejestracji i tam są błędy) -> Jeśli ok, to wraca na RevenuesView
    # Revenue -> Modal

class ExpensesView(LoginRequiredMixin, TemplateView):
    # Tabela mogłaby wyświetlać tylko część danych, a reszta w popupie po naciśnięciu?
    template_name = "expenses.html"

    def get_context_data(self, **kwargs):
        return {
            "expenses": Expense.objects.all().order_by("document_date"),
            "expense_form": AddRevenueForm
        }

# Manager views

class IncomeStatementView(
    LoginRequiredMixin, TemplateView
):
    template_name = "income_statement.html"

    # change this dispatch into a decorator somehow?
    def dispatch(self, request, *args, **kwargs):

        user_groups = [
            group for group in request.user.groups.values_list(
                'name', flat=True
            )
        ]

        if str(request.user.companymember.company.id) == self.kwargs["pk"]\
                and "Managers" in user_groups:
            return super(IncomeStatementView, self).dispatch(
                request, *args, **kwargs
            )
        else:
            return HttpResponseForbidden('Forbidden.')


    def get_context_data(self, **kwargs):
        # ToDo: Currently counts total revenues

        # ToDo: Dodać filtrowanie po id firmy, później po okresie - od początku roku

        year_beginning = date(date.today().year, 1, 1)
        year_end = date(date.today().year, 12, 31)
        month_beginning = date(date.today().year, date.today().month, 1)

        return {
            "total_net_revenues" : revenue_calculator(
                self.kwargs["pk"], year_beginning, year_end
            )
        }

# Second path
# class IncomeStatementView(
#     LoginRequiredMixin, TemplateView
# ):
#
#     @method_decorator(permission_required_or_403('dashapp.view_company',
#                                                  (Company, 'pk', 'pk'),
#                                                  accept_global_perms=True))
#     def dispatch(self, request, *args, **kwargs):
#         print()
#         permission_required = "company_" + str(self.kwargs["pk"])
#         return super(IncomeStatementView, self).dispatch(
#             request, *args, **kwargs
#         )
#
#     # ToDo: Currently counts total revenues
#     template_name = "income_statement.html"
#
#     # ToDo: Dodać filtrowanie po id firmy, później po okresie - od początku roku
#     revenue_data = Revenue.objects.all()
#     total_net_revenues = 0
#     # ToDo: Zaokrąglić
#     for revenue in revenue_data:
#         total_net_revenues += revenue.net_amount_converted
#
#     def get_context_data(self, **kwargs):
#         return {
#             "total_net_revenues": self.total_net_revenues
#         }

# Old version
# class IncomeStatementView(
#     LoginRequiredMixin, GroupRequiredMixin, TemplateView
# ):
#
#     # Checks for employee-type group, the company group is checked within the
#     # custom mixin GroupRequiredMixin
#     group_required = ["Managers"]
#
#
#     # def get_group_required(self):
#     #     return self.request.user.companymember.company.id
#
#     # group_required = ["Managers", "company_" + request.user.companymember.company.id]
#
#
#
#     # ToDo: Currently counts total revenues
#     template_name = "income_statement.html"
#
#     # ToDo: Dodać filtrowanie po id firmy, później po okresie - od początku roku
#     revenue_data = Revenue.objects.all()
#     total_net_revenues = 0
#     # ToDo: Zaokrąglić
#     for revenue in revenue_data:
#         total_net_revenues += revenue.net_amount_converted
#
#     def get_context_data(self, **kwargs):
#         return {
#             "total_net_revenues" : self.total_net_revenues
#         }

class CashFlowView(
    LoginRequiredMixin, TemplateView
):
    template_name = "cash_flow.html"

    # change this dispatch into a decorator somehow?
    def dispatch(self, request, *args, **kwargs):

        user_groups = [
            group for group in request.user.groups.values_list(
                'name', flat=True
            )
        ]

        if str(request.user.companymember.company.id) == self.kwargs["pk"]\
                and "Managers" in user_groups:
            return super(CashFlowView, self).dispatch(
                request, *args, **kwargs
            )
        else:
            return HttpResponseForbidden('Forbidden.')


    def get_context_data(self, **kwargs):
        # ToDo: Currently counts total revenues

        # ToDo: Dodać filtrowanie po id firmy, później po okresie - od początku roku

        year_beginning = date(date.today().year, 1, 1)
        year_end = date(date.today().year, 12, 31)
        month_beginning = date(date.today().year, date.today().month, 1)

        return {

        }

class ModificationDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "modification_dashboard.html"
