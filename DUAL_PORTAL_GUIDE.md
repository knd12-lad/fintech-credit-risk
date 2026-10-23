# 🌐 RiskWise — Single Browser Dual-Portal Guide (Google Chrome)

This guide explains how to run the **Admin Portal** and the **User / Borrower Portal** side-by-side in the same **Google Chrome** browser on the **exact same address** (`http://127.0.0.1:8000/` or `http://localhost:8000/`).

આ ગાઇડમાં એક જ **Google Chrome** બ્રાઉઝરમાં એક જ સરનામાં પર (Same Address) સાઇડ-બાય-સાઇડ **Admin Portal** અને **User / Borrower Portal** બંને એકસાથે ચલાવવાના સરળ સ્ટેપ્સ આપેલા છે.

---

## 📌 Architecture: Dedicated Session Cookies (Why This Works)
RiskWise uses `SplitSessionMiddleware` to completely decouple portal sessions:
- **Admin Portal (`/admin/*`)**: Operates on a dedicated session cookie named **`rw_admin_sessionid`**.
- **Public / Borrower Website (`/*`)**: Operates on the standard session cookie **`sessionid`**.

Because the two cookie namespaces are completely separate, an admin logging into `/admin/` never affects the public website, and logging out on one portal never terminates the other. You can use the exact same hostname and port (`http://127.0.0.1:8000/` or `http://localhost:8000/`) for both sides without domain tricks or incognito windows!

---

## 🚀 Step-by-Step Instructions:

### 1. સર્વર શરૂ કરો (Start Server)
```powershell
$env:OPENBLAS_NUM_THREADS="1"
python manage.py runserver
```

---

### 2. ડાબી ટેબ: Admin Portal (Left Tab)
1. તમારા **Google Chrome** માં નવી ટેબ ખોલો.
2. URL એડ્રેસ બારમાં આ લિંક પેસ્ટ કરો:
   ```
   http://127.0.0.1:8000/admin/
   ```
3. **Admin Credentials** થી લૉગિન કરો:
   * **Email / Username:** `fintech26@gmail.com` (અથવા તમારું એડમિન આઈડી)
   * **Password:** તમારો એડમિન પાસવર્ડ
4. અહીં તમને **RiskWise Admin Hub**, KPI Cards, Analytics, અને Live Predictions Dashboard જોવા મળશે.

---

### 3. જમણી ટેબ: User / Borrower Portal (Right Tab)
1. તે જ **Google Chrome** માં બીજી ટેબ (અથવા સ્પ્લિટ વિન્ડો) ખોલો.
2. તે જ સરનામાં પર પબ્લિક વેબસાઇટ ખોલો:
   ```
   http://127.0.0.1:8000/
   ```
3. વેબસાઇટ સામાન્ય મુલાકાતી તરીકે ખુલે છે (એડમિન સેશન અહીં લીક થતું નથી).
4. **Login** પેજ પર જાઓ: `http://127.0.0.1:8000/login/`
5. સામાન્ય યુઝર (Borrower) તરીકે લૉગિન કરો:
   * **Email:** `borrower1@example.com`
   * **Password:** `StrongPassword123!`
   * અથવા **Register** પરથી નવો એકાઉન્ટ બનાવી લો.

---

### 4. લાઈવ ટેસ્ટિંગ કેવી રીતે કરવું (Live Testing Flow):
1. **જમણી ટેબ (User side):**  
   * **"Risk Checker"** પેજ પર જાઓ (`http://127.0.0.1:8000/risk-checker/`).  
   * લોનની વિગતો (Age, Income, Loan Amount, Purpose) ભરીને **"Predict Risk"** બટન દબાવો.
2. **ડાબી ટેબ (Admin side):**  
   * પેજને **Refresh (F5)** કરો.  
   * તમે જોશો કે:
     * **Total Applications** કાઉન્ટ ૧ વધી જશે!
     * **Average Credit Score** અને **Predicted Default Rate** રીકેલ્ક્યુલેટ થશે!
     * નવી લોન એપ્લિકેશન એડમિન ડેશબોર્ડમાં તાત્કાલિક દેખાશે!

---

## ⚡ Quick Summary:
| Side | Browser | URL | Session Cookie | Logged-in Role |
| :--- | :--- | :--- | :--- | :--- |
| **ડાબી બાજુ (Left Side)** | Google Chrome | `http://127.0.0.1:8000/admin/` | `rw_admin_sessionid` | **RiskWise Admin / Staff** |
| **જમણી બાજુ (Right Side)** | Google Chrome | `http://127.0.0.1:8000/` | `sessionid` | **Borrower / Normal User** |
