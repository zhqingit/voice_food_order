# AI assistant food online order system
## Description
This is a AI assistant that can chat with users to order food and send the orders to the food stores. 
What does will system do:
1. When user calls the restaurant, the system will automatically response the call
2. The system will understand user's requirement and help user order the food
## Architeture
The system consists of backend and frontend sides.
### Backend
The backend is written by fastapi associated with Postgres database. The core function is an AI agent that can chat with the users and order the food given the menu of the store. 
#### Database
- User
    - user settings
    - user order history
- Store
    - store settings
    - store menu
    - store order history
#### AI assistant
- General AI
    - gpt
    - gemini
- Architecture: TBD
### Frontend
#### Android and Apple app
The app is used by user to talk to the food order agent to order the food
- Functions:
    - Chat with AI
    - Display all registered stores
    - Search nearest store by address
    - Search store by food style
- Layout (Card based)
    - First layer: manual and vocie buttons
    - Second layer:
        - manual
            - search by address
            - search by name
            - search by food style
        - voice
            - chat with AI
            - a window showing the food already ordered
    - Third layer:
        - manual
            - list the foods
            - a window to show the food already ordered
- Style
    - simple and clean 
    - futuristic
    - blue + green color
    - add transparent feature 
- both authticated and unauthticated modes work

#### Website
The website is running on the server by which the food store can login and change the settings.
- Functions:
    - Store profiles
    - Input and update the menu
    - Order time update
    - Order status display
    - Add specific requirements
    - Connecting to order printer
- Layout (Dashboard based)
    - Profiles 
        - store basic information
        - payment
        - settings to order printer
    - Menu input and update
    - Orders display
    - Specific requirments

- Style
    - simple and clean 
    - futuristic
    - blue + green color
    - add transparent feature 

- Registered store only
