# Important
* Check ZIMRA response email
* qrcodes have valid url but saying the invoice is not validated since we have fiscal day errors (assumption), we wait on ZIMRA to reset fiscal day so we see if that fixes the issue
* Create close fiscal day function
* go live with ecocash gateway
* deploy on hostinger vps and configure domain
* Useful links [ZIMRA API](https://fdmsapitest.zimra.co.zw/swagger/index.html) and [ZIMRA API DOC](ZIMRA_DOCS/Fiscal%20Device%20Gateway%20API%20v6.0%20-%20clients.pdf)

# ✅ Task List & Development Notes

- YOU ARE GETTING INVOICES FROM QB ONLINE. <ADVICE>
- IF YOU ARE NOT GETTING ANY MAKE SURE TO RE_SAVE THE WEBHOOK <ADVICE>
- WE ARE GETTING data from webhook odoo v17 <ADVICE>
- Noticed we have no customer on invoice and their on tax reg number <DONE>
- ALSO FIX THE AMOUNT ON THE INVOICE_PRODUCT GET THE CORRECT TAX AMOUNT <DONE>
- get customer from qb <DONE>
- create webhook for pos sales <DONE>
- turned off csrf validation ~ this might be an issue down the line <ADVICE>
- create field to enable/disable fiscalise on invoice <DONE>
- create function to create excel from form of zimra in zimra
- create a function that sends an email to ZIMRA requesting access for that client cc client
- once access is given back the user can fill in the information received back into the system
- we could use AI here <ADVICE>
- customer unique by tax reg number per organisation do it on customer create <NOT NECESSARY>
- sage intergration
- zimra fiscalisation <IN PROGRESS>
- when you unsubscribe tax also delete config for that tax

- EACH ZIMRA TAXLINE SEEMS TO HAVE THE SAME TAX, WE NEED TO GET TAX FOR EACH LINE IN ALL SOFTWARE
- SEND FISCALISATION TO ZIMRA
- Google sign in error mismatch url <DONE>
- waiting for key from zimra to complete registration
- then go and test fiscalisation
- connected multiple instances of apps to a app connector (odoo tested)
- sign in and signup workflow verified

---

## 📍 WHERE ARE WE NOW

-- this will be a lot, here is the plan:

* **INVOICE FISCALISATION ERROR LISTS**

  We need to solve RTC error list returned when we submit an invoice.  
  This includes making sure state is `submitted` not `fiscalised`.  
  We must find a way to store these error lists and show them to the user.  
  Also create a **retry function** in each app, allowing users to resend to **Taxman**,  
  which will then resend the same invoice with adjustments.

* **POST FISCALISATION ACTIONS**

  These are actions that must be performed *after* fiscalisation:  
  - Checking certificate validity  
  - Generating QR code  
  - Sending QR code back to the originating app  
  
  Consider creating a **signal** (like a webhook) that sends this response back to the calling app.

---

- we must do all this for credit notes
- you are left to integrate sage and excel
- also must make sure that resubmitting of invoices when failure and fixing errors if the invoice has been adjusted