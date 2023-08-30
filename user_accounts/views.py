from django.shortcuts import render
from .forms import UserForm,UserProfileInfoForm
from django.contrib.auth import authenticate, login, logout
from django.http import HttpResponseRedirect, HttpResponse
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from . import models
from .forms import SearchHandle
from .models import languages, verdicts, levels

from bs4 import BeautifulSoup
import requests
from lxml import html

import pandas as pd
import matplotlib.pyplot as plt, mpld3


from collections import OrderedDict
from . import fusioncharts



# Create your views here.

def index(request):
	return render(request, 'accounts/index.html')

@login_required
def special(request):
    return HttpResponse("You are logged in !")

def dashboard(request):
	return render(request, 'accounts/dashboard.html')


@login_required
def user_logout(request):
    logout(request)
    return HttpResponseRedirect(reverse('index'))


def signup(request):
    registered = False
    if request.method == 'POST':
        user_form = UserForm(data=request.POST)
        profile_form = UserProfileInfoForm(data=request.POST)
        if user_form.is_valid() and profile_form.is_valid():
            user = user_form.save()
            user.set_password(user.password)
            user.save()
            profile = profile_form.save(commit=False)
            profile.user = user
            if 'profile_pic' in request.FILES:
                print('found it')
                profile.profile_pic = request.FILES['profile_pic']
            profile.save()
            registered = True
        else:
            print(user_form.errors,profile_form.errors)
    else:
        user_form = UserForm()
        profile_form = UserProfileInfoForm()
    return render(request,'accounts/signup.html',
                          {'user_form':user_form,
                           'profile_form':profile_form,
                           'registered':registered})

def user_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(username=username, password=password)
        if user:
            if user.is_active:
                login(request,user)
                return HttpResponseRedirect(reverse('index'))
            else:
                return HttpResponse("Your account was inactive.")
        else:
            print("Someone tried to login and failed.")
            print("They used username: {} and password: {}".format(username,password))
            return HttpResponse("Invalid login details given")
    else:
        return render(request, 'accounts/login.html', {})


# def stats(request):
# 	return render(request, 'accounts/stats.html')

def schedule(request):
	colz = tt_generator()
	return render(request, 'accounts/schedule.html' , {"cols" : colz})
	# PUT STUFF HERE

def tt_generator() :
    
    page = requests.get("http://codeforces.com/contests")
    soup = BeautifulSoup(page.content, 'html.parser')
    #table1 = []
    table1 = soup.find('div' , attrs = {'class' : 'datatable'})
    if table1 is None:
        return
    rows = table1.find_all('tr')
    del rows[0]
    #rows
    #cols = rows[1].find_all('td')
    cnt = 0
    
    for row in rows :
        cols = row.find_all('td')
        cols = [x.text.strip() for x in cols]
        
        yield cols


# def signup(response):
#     if response.method == 'POST':
#         form = RegisterForm(response.POST)
#         if form.is_valid() :
#             form.save()
#         return redirect('/dashboard')

#     else :
#         form = RegisterForm()
#     return render(response, 'accounts/signup.html', {"form" : form})



# def login(request):
#     return render(request, 'accounts/login.html')



def stats(request):

    # OneToOne Field hai user in UserProfileInfo model to usko access karne
    # ka tareeka!!!    
    profile = request.user.userprofileinfo
    handle = profile.cf_handle

    fcs = fetch_contest_stats(handle)
    chart = {"output_languages" :  display_stats_languages(handle).render(),
            "output_verdicts" :  display_stats_verdicts(handle).render(),
            "output_levels" :  display_stats_levels(handle).render(),
    }

    fcs.update(chart)

    return render(request, 'accounts/contest_stats.html', fcs)

    profile = request.user.userprofileinfo
    handle = profile.cf_handle
    fcs = fetch_contest_stats(handle)

    submissionsFigure(request)

    return render(request, 'accounts/figure_html.html', fcs)


def submissionsFigure(request):
    profile = request.user.userprofileinfo
    handle = profile.cf_handle

    df = fetchSubmissionDetails(handle)

    lang_occurence_data = df['Lang'].value_counts()

    labels = lang_occurence_data.keys().tolist()
    sizes = lang_occurence_data.values

    fig = plt.figure()
    plt.pie(sizes, labels=labels)

    html_fig = mpld3.fig_to_html(fig)

    html_fig = "{% extends 'accounts/base.html' %} \n {% block content %} \n" + html_fig + "{% endblock %}"

    file = open('templates/accounts/figure.html', "w")
    file.write(html_fig)
    file.close()


def fetch_contest_stats(handle):
    start_url = "https://www.codeforces.com/"

    cf_handle = handle
    contests_url = start_url+'contests/with/'+cf_handle

    page = requests.get(contests_url)
    soup = BeautifulSoup(page.content, 'lxml')


    table = soup.find('table', class_='tablesorter user-contests-table')
    tbody = table.find('tbody')

    ROWS = tbody.find_all('tr')

    delta_rating = []
    rank_list = []

    for item in ROWS:
        elements = item.find_all('td')
        rank = int(elements[2].find('a').text)
        rating_change = int(elements[4].text)

        delta_rating.append(rating_change)
        rank_list.append(rank)

    delta_rating.sort()
    rank_list.sort()

    mydict = {
        'Handle' : cf_handle,
        'No_of_Contests' : ROWS[0].find('td').text,
        'Best_Rank' : rank_list[0],
        'Worst_Rank' : rank_list[len(rank_list)-1],
        'Max_Up' : delta_rating[len(delta_rating)-1],
        'Max_Down' : delta_rating[0],
    }

    return mydict