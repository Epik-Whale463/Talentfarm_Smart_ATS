# GitHub OAuth Setup Instructions

To properly set up GitHub OAuth authentication for the ATS application, follow these steps:

## 1. Register a new OAuth Application on GitHub

1. Go to your GitHub account settings
2. Navigate to **Settings** > **Developer settings** > **OAuth Apps**
3. Click **New OAuth App**
4. Fill in the application details:
   - **Application name**: AI-ATS
   - **Homepage URL**: `http://localhost:5000`
   - **Application description**: (Optional) AI-Powered Applicant Tracking System
   - **Authorization callback URL**: `http://localhost:5000/api/auth/github/authorize`
5. Click **Register application**

## 2. Get your Client ID and Client Secret

1. After registration, you'll be taken to your new OAuth app's page
2. Note your **Client ID** which is displayed on this page
3. Click **Generate a new client secret**
4. Copy the generated secret immediately (you won't be able to see it again)

## 3. Update the ATS application configuration

Create a `.env` file in the root directory of your project with the following contents:

```
GITHUB_CLIENT_ID=your_client_id_here
GITHUB_CLIENT_SECRET=your_client_secret_here
GITHUB_CALLBACK_URL=http://localhost:5000/api/auth/github/authorize
```

Replace `your_client_id_here` and `your_client_secret_here` with the values from GitHub.

## 4. Restart the application

After updating the `.env` file, restart the Flask application:

```
python app.py
```

## Troubleshooting

- If you see "redirect_uri is not associated with this application" error, make sure the callback URL in your GitHub OAuth app settings exactly matches the one in your configuration.
- The callback URL is case-sensitive and must include the correct protocol (http:// or https://).
- If you're hosting the application somewhere other than localhost, update all URLs accordingly.
- For production deployment, you should use HTTPS for security.
