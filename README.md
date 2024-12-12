# Eve Online Odoo Integration

## Description
This repository contains custom Odoo modules for integrating Eve Online functionalities into Odoo. The goal is to manage an Eve Online corporation using Odoo, including inventory, manufacturing, market data, and member management.

## Modules
- **Eve Online Login**: OAuth authentication with Eve Online.
- **Inventory Sync**: Synchronizes inventory data from Eve Online.
- **Bill of Materials (BOM)**: Manages Eve Online BOMs within Odoo.
- **Market Data Integration**: Fetches and analyzes market data.
- **Recruitment and Onboarding**: Manages recruitment and onboarding processes.
- **In-Game Messaging**: Sends in-game messages to Eve Online players.

## Roadmap
1. **User Authentication and Basic Integration**
2. **Inventory and Manufacturing Management**
3. **Market and Financial Management**
4. **Recruitment and Member Management**
5. **In-Game Messaging and Communication**

## Configuration

To set up the environment variables, follow these steps:

1. **Create a `.env` file** in the root directory of the project.
2. **Copy the content** from `.env.example` into your `.env` file.
3. **Replace** the placeholder values with your actual credentials and URLs.

To set up the environment variables, create a `.env` file in the root directory of the project with the following content:

### Example of `.env` File:

```bash
EVE_CLIENT_ID=your_client_id
EVE_CLIENT_SECRET=your_client_secret
EVE_REDIRECT_URI=your_redirect_uri
```

## Installation

1. **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

2. **Run the server**:
    ```bash
    python integration_service/app.py
    ```

Ensure your `.env` file is correctly configured with your credentials and URLs before running the server.

## Contributing
Contributions are welcome! Please fork the repository and submit pull requests for review.

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.