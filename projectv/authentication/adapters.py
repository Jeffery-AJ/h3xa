# from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
# from django.contrib.auth.models import User
# import requests
# from django.shortcuts import redirect

# class SocialAccountAdapterV2(DefaultSocialAccountAdapter):
    
#     def pre_social_login(self, request, sociallogin):
#         # Check if the email already exists in the social login's extra data
#         email = sociallogin.account.extra_data.get('email')

#         # Get the username for fallback email generation
#         username = sociallogin.account.extra_data.get('login')

#         # If email doesn't exist in the extra data, try different approaches
#         if not email:
#             try:
#                 # First try: Get email from GitHub API
#                 social_token = sociallogin.account.socialtoken_set.first()
#                 if social_token:
#                     email = self.fetch_email_from_github(social_token.token)
                    
#                     # Second try: If API doesn't return email, use GitHub's noreply address
#                     if not email and username:
#                         # GitHub provides no-reply emails in the format: {id}+{username}@users.noreply.github.com
#                         # or newer format: {username}@users.noreply.github.com
#                         user_id = sociallogin.account.extra_data.get('id')
#                         if user_id:
#                             email = f"{user_id}+{username}@users.noreply.github.com"
#                         else:
#                             email = f"{username}@users.noreply.github.com"
#             except Exception as e:
#                 print(f"Error accessing GitHub data: {str(e)}")
                
#             # Store the email if we found one
#             if email:
#                 sociallogin.account.extra_data['email'] = email
        
#         # If email is available (either original or generated)
#         if email:
#             try:
#                 # Check if a user already exists with this email
#                 user = User.objects.get(email=email)
#                 # If a user exists, link the social account to the existing user
#                 sociallogin.user = user
#             except User.DoesNotExist:
#                 # If no user exists, the user will be created and linked
#                 pass
#         else:
#             # Last resort: Allow user to provide an email manually
#             # Store details in session and redirect to a custom form
#             if request and hasattr(request, 'session'):
#                 request.session['socialaccount_sociallogin'] = sociallogin.serialize()
#                 return redirect('custom_email_input')  # You'll need to create this view
            
#             # If redirect not possible, raise error
#             raise ValueError("Could not obtain or generate email for GitHub account")

#         return super().pre_social_login(request, sociallogin)
       
#     def fetch_email_from_github(self, token):
#         url = 'https://api.github.com/user/emails'
#         headers = {
#             'Authorization': f'token {token}',
#             'Accept': 'application/vnd.github.v3+json'
#         }
        
#         try:
#             response = requests.get(url, headers=headers)
            
#             if response.status_code == 200:
#                 emails = response.json()
                
#                 # Try to get any verified email (primary preferred)
#                 primary_verified = next((e['email'] for e in emails if e.get('verified') and e.get('primary')), None)
#                 if primary_verified:
#                     return primary_verified
                    
#                 # Fall back to any verified email
#                 any_verified = next((e['email'] for e in emails if e.get('verified')), None)
#                 if any_verified:
#                     return any_verified
                    
#                 # Last resort: any email at all
#                 any_email = next((e['email'] for e in emails if 'email' in e), None)
#                 return any_email
                
#             return None
#         except Exception as e:
#             print(f"Error in GitHub API request: {str(e)}")
#             return None