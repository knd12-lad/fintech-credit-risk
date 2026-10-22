# 🌐 RiskWise — Single Browser Dual-Portal Guide (Google Chrome)

આ ગાઇડમાં એક જ **Google Chrome** બ્રાઉઝરમાં સાઇડ-બાય-સાઇડ (Side-by-Side) **Admin Portal** અને **User / Borrower Portal** બંને એકસાથે ચલાવવાના સંપૂર્ણ સ્ટેપ્સ આપેલા છે.

---

## 📌 મહત્વનું રહસ્ય (Why This Works):
ક્રોમ બ્રાઉઝર **`127.0.0.1:8000`** અને **`localhost:8000`** ને બે અલગ ડોમેઇન (Domains) ગણે છે. તેથી બંને ટેબ એક જ સામાન્ય ગૂગલ ક્રોમમાં ખુલ્લી હોવા છતાં તેમના લૉગિન સેશન કૂકીઝ (Session Cookies) એકબીજા સાથે અથડાતા (clash) નથી!

---

## 🚀 Step-by-Step Instructions:

### ૧. સર્વર શરૂ કરો (Start Server)
```powershell
python manage.py runserver
```

---

### ૨. ડાબી ટેબ: Admin Portal (Left Tab)
1. તમારા **Google Chrome** માં નવી ટેબ ખોલો.
2. URL એડ્રેસ બારમાં આ લિંક પેસ્ટ કરો:
   ```
   http://127.0.0.1:8000/admin/
   ```
3. **Admin Credentials** થી લૉગિન કરો:
   * **Email / Username:** `admin@riskwise.test` (અથવા તમારું સુપરયુઝર આઈડી)
   * **Password:** તમારો એડમિન પાસવર્ડ
4. અહીં તમને **RiskWise Admin Hub**, KPI Cards, Analytics, અને Live Predictions Dashboard જોવા મળશે.

---

### ૩. જમણી ટેબ: User / Borrower Portal (Right Tab)
1. તે જ **Google Chrome** માં બીજી ટેબ (અથવા સ્પ્લિટ વિન્ડો) ખોલો.
2. URL એડ્રેસ બારમાં ખાસ આ લિંક પેસ્ટ કરો (`127.0.0.1` નહીં, પણ `localhost`):
   ```
   http://localhost:8000/
   ```
3. જો ત્યાં પહેલેથી એડમિન લૉગિન દેખાતું હોય તો:
   * ઉપર પ્રોફાઇલ પર ક્લિક કરી **Logout** કરો.
   * પછી **Login** પેજ પર જાઓ: `http://localhost:8000/login/`
   * સામાન્ય યુઝર (Borrower) તરીકે લૉગિન કરો:
     * **Email:** `borrower1@example.com`
     * **Password:** `StrongPassword123!`
   * અથવા **Register** પરથી નવો યુઝર બનાવી લો.

---

### ૪. લાઈવ ટેસ્ટિંગ કેવી રીતે કરવું (Live Testing Flow):
1. **જમણી ટેબ (User side - localhost):**  
   * **"Risk Checker"** પેજ પર જાઓ (`http://localhost:8000/check-risk/`).  
   * લોનની વિગતો (Age, Income, Loan Amount, Purpose) ભરીને **"Predict Risk"** બટન દબાવો.
2. **ડાબી ટેબ (Admin side - 127.0.0.1):**  
   * પેજને **Refresh (F5)** કરો.  
   * તમે જોશો કે:
     * **Total Applications** કાઉન્ટ ૧ વધી જશે!
     * **Average Credit Score** અને **Predicted Default Rate** રીકેલ્ક્યુલેટ થશે!
     * **14-Days Line Graph** અને **Risk Breakdown Doughnut Graph** માં નવો ડેટા આપોઆપ આવી જશે!

---

## ⚡ Quick Summary:
| Side | Browser | URL | Logged-in User |
| :--- | :--- | :--- | :--- |
| **ડાબી બાજુ (Left Side)** | Google Chrome | `http://127.0.0.1:8000/admin/` | **RiskWise Master Admin** |
| **જમણી બાજુ (Right Side)** | Google Chrome | `http://localhost:8000/` | **Borrower / Normal User** |
