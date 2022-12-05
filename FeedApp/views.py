from django.shortcuts import render, redirect
from .forms import PostForm,ProfileForm, RelationshipForm
from .models import Post, Comment, Like, Profile, Relationship
from datetime import datetime, date

from django.contrib.auth.decorators import login_required
from django.http import Http404


# Create your views here.

# When a URL request matches the pattern we just defined, 
# Django looks for a function called index() in the views.py file. 

def index(request):
    """The home page for Learning Log."""
    return render(request, 'FeedApp/index.html')


#decorator, func to do verification , in order to access following functions ,
#prevent unauthorized access to db ,posting
@login_required

def profile(request): 
    #check if its a creating a new profile or updating existing 
    #refer to person currently logged on to the system
    #NOTES:get does not work with exists()

    profile = Profile.objects.filter(user=request.user)
    if not profile.exists():
        Profile.objects.create(user=request.user)
    profile = Profile.objects.get(user=request.user)

    if request.method != 'POST':
        form = ProfileForm(instance=profile)
    else:
        form = ProfileForm(instance=profile,data=request.POST)
        if form.is_valid():
            form.save()
            return redirect('FeedApp:profile')
    context={'form':form}
    return render(request, 'FeedApp/profile.html', context)

@login_required
def myfeed(request):
    #empty lists to hold the num comments and likes , since we have multiple posts
    comment_count_list = []
    like_count_list = []
    posts = Post.objects.filter(username=request.user).order_by('-date_posted')
    for p in posts:
        c_count = Comment.objects.filter(post = p).count()
        l_count = Like.objects.filter(post = p).count()
        comment_count_list.append(c_count)
        like_count_list.append(l_count)
    #each post can have their comment and likes together
    zipped_list = zip(posts,comment_count_list,like_count_list)
    context ={'posts':posts,'zipped_list':zipped_list}
    return render(request, 'FeedApp/myfeed.html', context)

@login_required
def new_post(request):
    if request.method != 'POST':
        form = PostForm()
    else:
        form = PostForm(request.POST,request.FILES)
        if form.is_valid():
            new_post = form.save(commit=False) 
            new_post.username = request.user 
            new_post.save()
            return redirect('FeedApp:myfeed')
    context={'form':form}
    return render(request, 'FeedApp/new_post.html', context)

@login_required
def friendsfeed(request):
    comment_count_list = []
    like_count_list = []
    friends = Profile.objects.filter(user=request.user).values('friends')
    posts = Post.objects.filter(username__in=friends).order_by('-date_posted')
    for p in posts:
        c_count = Comment.objects.filter(post = p).count()
        l_count = Like.objects.filter(post = p).count()
        comment_count_list.append(c_count)
        like_count_list.append(l_count)
    #each post can have their comment and likes together
    zipped_list = zip(posts,comment_count_list,like_count_list)

    #check if the like button is clicked or not
    if request.method == 'POST' and request.POST.get("like"):
        post_to_like = request.POST.get("like")
        print(post_to_like)
        #make sure only 1person can like once
        like_already_exists = Like.objects.filter(post_id=post_to_like,username=request.user)
        if not like_already_exists():
            Like.objects.create(post_id=post_to_like,username=request.user)
            return redirect("FeedApp:friendsfeed")


    context ={'posts':posts,'zipped_list':zipped_list}
    return render(request, 'FeedApp/friendsfeed.html', context)

#if anybody has clicked the button
@login_required
def comments(request,post_id):
        if request.method == 'POST' and request.POST.get("btn1"):
            comment = request.POST.get("comment")
            Comment.objects.create(post_id = post_id,username=request.user,text=comment,date_added=date.today())

        #refresh the page with new comments submitted
        comments=Comment.objects.filter(post=post_id)
        post = Post.objects.get(id=post_id)
        context={'post':post,'comments':comments}
        return render(request, 'FeedApp/comments.html', context)

#friend requests , friends that we have, sent request , asked to be our friend , make sure admin is automatic friend request sent 
@login_required
def friends(request):

    #get the admin profile and user profile to create the first relationship
    admin_profile = Profile.objects.get(user=1)
    user_profile = Profile.objects.get(user=request.user)

    #to get list of users friends in order to display
    user_friends = user_profile.friends.all()
    user_friends_profiles = Profile.objects.filter(user__in=user_friends)

    #list of sent friend requests , collection of all profiles
    user_relationships = Relationship.objects.filter(sender=user_profile)
    request_sent_profiles = user_relationships.values('receiver')

    #list of who we can send friend requests --> show other people in our system(not friends yet) 
    # and also to whom we have not sent a req

    #eligble profiles - exclude the user, their existing friends, and friend requests sent already
    all_profiles = Profile.objects.exclude(user=request.user).exclude(id__in=user_friends_profiles).exclude(id__in=request_sent_profiles)

    #get list of friend requests received by the user
    request_received_profiles = Relationship.objects.filter(receiver=user_profile,status='sent')

    #if this is the first time to access the friend request page , create 1st relationship
    #with the admin of the website (so admin is friend with everyone)
    if not user_relationships.exists():
        Relationship.objects.create(sender=user_profile,receiver=admin_profile,status='sent')

    #to check which submit button was pressed (sending a friend req or accepting a friend req?)

    #process all sent req (note: send_requests object is checkboxes in html), value of checkbox is id of the profile
    if request.method == 'POST' and request.POST.get("send_requests"):
        #list of people/ids who are recivers of friend req
        receivers  = request.POST.getlist("send_requests")
        for receiver in receivers:
            receiver_profile = Profile.objects.get(id=receiver)
            Relationship.objects.create(sender=user_profile,receiver=receiver_profile,status='sent')
        return redirect('FeedApp:friends')

    #process all req that has been received
    if request.method == 'POST' and request.POST.get("receive_requests"):
        #list of people/ids who are senders of friend req
        senders  = request.POST.getlist("friend_requests")
        for sender in senders:
            #update the relationship model for the sender to status 'accepted'
            Relationship.objects.filter(id=sender).update(status='accepted')

            #create a relationship object to access the sender's user id
            #to add to the friends list of the user 
            relationship_obj = Relationship.objects.get(id=sender)
            user_profile.friends.add(relationship_obj.sender.user)

            #add the user to the friends list of sender's profile
            relationship_obj.sender.friends.add(request.user)
    context={'user_friends_profiles':user_friends_profiles,'user_relationships':user_relationships,
    'all_profiles':all_profiles,'request_received_profiles':request_received_profiles}

    return render(request, 'FeedApp/friends.html', context)











   





