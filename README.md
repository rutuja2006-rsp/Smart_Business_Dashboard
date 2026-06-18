#  Smart Business Dashboard

An interactive  Business Intelligence Dashboard that provides data analysis, visualization, and forecasting for sales and product datasets with a secure authentication system.

---

##  Features

###  User Authentication
- Secure login & signup system
- Password hashing (bcrypt / SHA-256 fallback)
- Account lock after multiple failed attempts
- Session management using Streamlit

---

###  Dataset Handling
- Upload CSV files directly
- Automatic dataset type detection:
  - Sales dataset
  - Product / Review dataset
- Smart column detection (no fixed format required)

---

###  Data Analysis & Visualization
- Sales & revenue analysis
- Category-wise performance
- Product-level insights
- Rating distribution analysis
- Interactive charts using Plotly

---

###  Smart Insights
- Best & worst performing products
- Profitability analysis
- Customer rating trends
- Discount and pricing insights
- Category performance comparison

---

###  Forecasting
- Sales prediction using Linear Regression
- Future trend estimation
- Actual vs predicted visualization

---

###  Export Options
- Download raw dataset
- Download processed dataset
- Generate summary report (TXT)

---

##  Tech Stack

- Python 
- Streamlit
- Pandas & NumPy
- Plotly
- Scikit-learn
- SQLite (Database)
- HTML/CSS (UI Styling)

---
##  Project Structure


Smart-Business-Dashboard/
│
├── app.py # Backup / experimental version (optional)
├── app1(1).py # Main Streamlit application (final version)
├── app.db # Application database 
├── users.db # User authentication database
├── pydeck.json # Map configuration (PyDeck visualization data)
├── README.md # Project documentation


---

##  How to Run

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run app1 (1).py


##  Screenshots

###  Login Page
<img width="1600" height="846" alt="image" src="https://github.com/user-attachments/assets/2968ffa0-6854-4c37-b961-2b7bf99cca7b" />


###  Dashboard
<img width="1600" height="795" alt="image" src="https://github.com/user-attachments/assets/e474c736-ca7e-488e-ad30-2d15e0c5e61e" />


###  Analysis

<img width="1600" height="808" alt="image" src="https://github.com/user-attachments/assets/00975dfa-9a84-4c6b-94bc-03f2fb3baf67" />
<img width="1438" height="784" alt="image" src="https://github.com/user-attachments/assets/5115332a-d55b-4b72-b467-60219a73777c" />
<img width="1414" height="718" alt="image" src="https://github.com/user-attachments/assets/4200e931-93f9-42c8-a4b3-237773dcf20a" />

###  Insights
<img width="1507" height="910" alt="image" src="https://github.com/user-attachments/assets/bced28dd-bfd9-4e54-885f-8b325f174149" />








##  Future Improvements

- Integration of advanced machine learning models for better forecasting accuracy  
- Real-time data streaming support for live dashboards  
- Cloud deployment (Streamlit Cloud / AWS) for public access  
- Role-based access control for multiple user types  
- Enhanced visualization with geospatial mapping (PyDeck integration)

## 📁 Project Structure
