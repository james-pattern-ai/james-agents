# Guide to Obtaining and Configuring API Keys

This guide provides instructions for obtaining the necessary API keys for the comic cataloger project and configuring them in a `.env` file.

## Step 1: Obtain the API Keys

You will need to register for developer accounts on the following platforms to get your API keys:

1.  **Comic Vine API Key**
    *   **Website**: [https://comicvine.gamespot.com/api/](https://comicvine.gamespot.com/api/)
    *   **Instructions**:
        *   Go to the Comic Vine API page and look for a "Get an API Key" link or a similar registration process.
        *   You will likely need to create a free account on Gamespot.
        *   Once registered, you will be provided with an API key. Copy this key.

2.  **GoCollect API Key**
    *   **Website**: [https://gocollect.com/connect](https://gocollect.com/connect)
    *   **Instructions**:
        *   Visit the GoCollect Connect page.
        *   Sign up for a developer account. They may have free and paid tiers. A free tier is sufficient for this project's needs.
        *   After registration, find the API key in your developer dashboard.

3.  **eBay API Key (eBay Developer Program)**
    *   **Website**: [https://developer.ebay.com/](https://developer.ebay.com/)
    *   **Instructions**:
        *   Join the eBay Developer Program by creating an account.
        *   Once registered, you will need to create an "application" to get your credentials.
        *   Generate a set of "Production" keys. You will need the **App ID (Client ID)** and **Cert ID (Client Secret)** to generate an OAuth token, which serves as the `EBAY_TOKEN`.
        *   The process for generating an OAuth token is detailed in eBay's developer documentation. For this project, you'll likely need a "Client Credentials Grant" token.

## Step 2: Set up Google Cloud and Vertex AI Authentication

For the vision processing part of the project, the application needs to authenticate with Google Cloud to use Vertex AI services like the Gemma model.

1.  **Enable the Vertex AI API**:
    *   Go to the [Google Cloud Console](https://console.cloud.google.com/).
    *   Navigate to "APIs & Services" > "Library".
    *   Search for "Vertex AI API" and ensure it is enabled for your project.

2.  **Create a Service Account**:
    *   In the Cloud Console, go to "IAM & Admin" > "Service Accounts".
    *   Click "Create Service Account".
    *   Give it a name (e.g., "comic-cataloger-svc") and a description.
    *   Grant it the **"Vertex AI User"** role. You might also need "Cloud Storage Object Viewer" if your images are in a GCS bucket.
    *   Click "Done".

3.  **Create a Service Account Key**:
    *   Find the service account you just created in the list.
    *   Click the three-dot menu under "Actions" and select "Manage keys".
    *   Click "Add Key" > "Create new key".
    *   Choose **JSON** as the key type and click "Create".
    *   A JSON file containing your credentials will be downloaded. **Treat this file like a password.**

4.  **Set the Environment Variable**:
    *   Place the downloaded JSON key file in a secure location within your project (e.g., in the root directory, but ensure it's listed in your `.gitignore` file).
    *   You will set an environment variable named `GOOGLE_APPLICATION_CREDENTIALS` to point to the path of this JSON file.

## Step 3: Create the `.env` File

In the root directory of this project, create a new file named `.env`.

## Step 3: Add the Keys to the `.env` File

Open the `.env` file and add the keys you obtained in the following format. Replace the placeholder text with your actual keys.

```env
# .env file

# Google Cloud Credentials
# The path to your service account JSON key file.
# Make sure this file is included in your .gitignore.
GOOGLE_APPLICATION_CREDENTIALS="path/to/your/service-account-file.json"

# Comic Vine API Key
COMICVINE_KEY="your_comicvine_api_key_here"

# GoCollect API Key
GOCOLLECT_KEY="your_gocollect_api_key_here"

# eBay API Token (OAuth Token)
EBAY_TOKEN="your_ebay_oauth_token_here"
```

**Important Notes:**

*   **Do not share this file**: The `.env` file contains sensitive credentials and should not be committed to version control. The `.gitignore` file in this project should already be configured to ignore `.env` files.
*   **Restart the application**: After creating or modifying the `.env` file, you may need to restart the Python script for the new environment variables to be loaded.

Once you have completed these steps, I will be ready to run the system test again with the live API keys.