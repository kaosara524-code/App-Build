import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from supabase import create_client

# ==========================================
# ENTER YOUR SUPABASE INFO HERE
# ==========================================
URL = "https://zobuzeyqlqkwmlgqeare.supabase.co"
KEY = "sb_publishable_pLpJOnC5KtqCouUkBGuhzA_aP81rA3O"

# ডাটাবেস কানেকশন
supabase = None
try:
    supabase = create_client(URL, KEY)
except Exception as e:
    print(f"Database Connection Error: {e}")
    pass 

# ==========================================
# LOGIN SYSTEM (লগইন উইন্ডো)
# ==========================================
def login():
    user = entry_user.get()
    pwd = entry_pass.get()

    if not user or not pwd:
        messagebox.showwarning("Warning", "Please enter Username & Password")
        return

    try:
        if not supabase:
            messagebox.showerror("Error", "Database Connection Failed!")
            return

        response = supabase.table("users").select("*").eq("username", user).eq("password", pwd).execute()
        
        if response.data:
            role = response.data[0]['role']
            login_window.destroy()
            open_dashboard(user, role)
        else:
            messagebox.showerror("Error", "Wrong Username or Password!")
            
    except Exception as e:
        messagebox.showerror("Error", f"Login Error: {e}")

# ==========================================
# MAIN DASHBOARD (সফটওয়্যারের মূল অংশ)
# ==========================================
def open_dashboard(current_user, user_role):
    root = tk.Tk()
    root.title(f"TeleCity Pro - Logged in as: {current_user} ({user_role})")
    root.geometry("1200x800")
    root.configure(bg="white")

    # ডাটা রাখার লিস্ট
    customer_list = []
    
    # --- Logic Functions ---
    def load_customers():
        try:
            res = supabase.table("customers").select("name, code").execute()
            customer_list.clear()
            for r in res.data:
                customer_list.append(f"{r['name']} | {r['code']}")
            
            if 'combo_customer' in locals() or 'combo_customer' in dir():
                combo_customer['values'] = customer_list
        except: pass

    def check_due(event=None):
        full_text = combo_customer.get()
        if not full_text: return
        cust_name = full_text.split(" | ")[0]
        try:
            response = supabase.table("transactions").select("*").eq("customer_name", cust_name).execute()
            total_due = 0
            for row in response.data:
                amt = row['amount']
                if row['payment_method'] == 'Due/Baki': total_due += amt
                elif row.get('category') == 'Due Collection': total_due -= amt
            
            lbl_due_display.config(text=f"Current Due: {total_due} Tk")
            lbl_due_display.config(fg="red" if total_due > 0 else "green")
        except: pass

    def auto_suggest(event):
        if event.keysym in ['Return', 'Tab', 'Up', 'Down']: return
        typed = combo_customer.get()
        if typed == '': combo_customer['values'] = customer_list
        else:
            filtered = [item for item in customer_list if typed.lower() in item.lower()]
            combo_customer['values'] = filtered
            if filtered: combo_customer.event_generate('<Down>')

    def on_enter_pressed(event):
        if len(combo_customer['values']) > 0:
            combo_customer.set(combo_customer['values'][0])
            combo_customer.selection_clear()
            combo_customer.icursor(tk.END)
            check_due()

    def save_transaction():
        cust_text = combo_customer.get()
        cust_name = cust_text.split(" | ")[0] if cust_text else "General Customer"
        desc = entry_desc.get()
        amount = entry_amount.get()
        
        if desc and amount:
            try:
                data = {
                    "description": desc, "amount": int(amount), 
                    "type": combo_type.get(), "category": combo_cat.get(), 
                    "payment_method": combo_method.get(), "customer_name": cust_name, 
                    "entry_by": current_user
                }
                supabase.table("transactions").insert(data).execute()
                messagebox.showinfo("Success", "Transaction Saved!")
                entry_desc.delete(0, tk.END)
                entry_amount.delete(0, tk.END)
                check_due()
                update_dashboard()
            except Exception as e: messagebox.showerror("Error", str(e))

    def add_new_customer():
        name = entry_new_name.get()
        phone = entry_new_phone.get()
        
        if name:
            code = name[:3].upper() + phone[-3:]
            try:
                supabase.table("customers").insert({"name": name, "phone": phone, "code": code}).execute()
                messagebox.showinfo("Done", f"Customer Added! Code: {code}")
                entry_new_name.delete(0, tk.END)
                entry_new_phone.delete(0, tk.END)
                load_customers()
            except Exception as e: messagebox.showerror("Error", str(e))

    def update_dashboard():
        try:
            res = supabase.table("transactions").select("*").execute()
            df = pd.DataFrame(res.data)
        except: df = pd.DataFrame()
        if df.empty: return

        income = df[df['type'] == 'Income']['amount'].sum()
        expense = df[df['type'] == 'Expense']['amount'].sum()
        
        total_due = df[(df['type'] == 'Income') & (df['payment_method'] == 'Due/Baki')]['amount'].sum()
        due_col = df[df['category'] == 'Due Collection']['amount'].sum()
        market_due = total_due - due_col

        lbl_sales_val.config(text=f"{income:,}")
        lbl_exp_val.config(text=f"{expense:,}")
        lbl_profit_val.config(text=f"{income - expense:,}")
        lbl_due_val.config(text=f"{market_due:,}")

        for w in frame_graph.winfo_children(): w.destroy()
        fig, ax = plt.subplots(figsize=(5,3), dpi=100)
        ax.bar(['Income', 'Expense'], [income, expense], color=['green', 'red'])
        canvas = FigureCanvasTkAgg(fig, master=frame_graph)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def show_frame(frame):
        frame.tkraise()
        if frame == frame_entry: load_customers()
        elif frame == frame_home: update_dashboard()

    # --- UI Layout ---
    sidebar = tk.Frame(root, bg="#2c3e50", width=200)
    sidebar.pack(side="left", fill="y")
    tk.Label(sidebar, text="TeleCity", bg="#2c3e50", fg="white", font=("Arial", 20, "bold")).pack(pady=30)
    
    def mk_btn(txt, cmd): 
        tk.Button(sidebar, text=txt, bg="#34495e", fg="white", bd=0, font=("Arial", 12), pady=10, command=cmd).pack(fill="x", pady=2)

    content = tk.Frame(root, bg="white")
    content.pack(side="right", fill="both", expand=True)
    frame_home = tk.Frame(content, bg="white")
    frame_entry = tk.Frame(content, bg="white")
    frame_cust = tk.Frame(content, bg="white")
    
    for f in (frame_home, frame_entry, frame_cust): 
        f.place(x=0, y=0, relwidth=1, relheight=1)

    mk_btn("Dashboard", lambda: show_frame(frame_home))
    mk_btn("New Transaction", lambda: show_frame(frame_entry))
    mk_btn("Add Customer", lambda: show_frame(frame_cust))
    mk_btn("Logout", lambda: [root.destroy(), show_login_screen()])

    # Dashboard UI
    tk.Label(frame_home, text="Business Dashboard", font=("Arial", 22, "bold"), bg="white").pack(pady=20)
    f_cards = tk.Frame(frame_home, bg="white")
    f_cards.pack(fill="x", padx=20)
    
    def card(p, t, c):
        f = tk.Frame(p, bg=c, width=200, height=100)
        f.pack(side="left", fill="both", expand=True, padx=10)
        tk.Label(f, text=t, bg=c, fg="white").pack(pady=5)
        l = tk.Label(f, text="0", bg=c, fg="white", font=("Arial", 18, "bold"))
        l.pack()
        return l
    
    lbl_sales_val = card(f_cards, "TOTAL SALES", "#27ae60")
    lbl_exp_val = card(f_cards, "EXPENSE", "#c0392b")
    lbl_profit_val = card(f_cards, "PROFIT", "#2980b9")
    lbl_due_val = card(f_cards, "MARKET DUE", "#e67e22")
    frame_graph = tk.Frame(frame_home, bg="white")
    frame_graph.pack(fill="both", expand=True, padx=20, pady=20)

    # Entry UI
    tk.Label(frame_entry, text="Transaction Entry", font=("Arial", 20, "bold"), bg="white").pack(pady=20)
    f_form = tk.Frame(frame_entry, bg="#ecf0f1", padx=30, pady=30)
    f_form.pack()
    
    tk.Label(f_form, text="Customer Name:", bg="#ecf0f1", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="w")
    combo_customer = ttk.Combobox(f_form, width=30)
    combo_customer.grid(row=0, column=1, padx=5, pady=10)
    combo_customer.bind('<KeyRelease>', auto_suggest)
    combo_customer.bind('<Return>', on_enter_pressed)
    combo_customer.bind('<<ComboboxSelected>>', check_due)
    
    lbl_due_display = tk.Label(f_form, text="Due: 0 Tk", font=("Arial", 12, "bold"), bg="#ecf0f1", fg="gray")
    lbl_due_display.grid(row=0, column=2, padx=10)

    tk.Label(f_form, text="Description:", bg="#ecf0f1").grid(row=1, column=0, sticky="w")
    entry_desc = tk.Entry(f_form, width=32)
    entry_desc.grid(row=1, column=1, padx=5, pady=10)
    
    tk.Label(f_form, text="Amount:", bg="#ecf0f1").grid(row=2, column=0, sticky="w")
    entry_amount = tk.Entry(f_form, width=32)
    entry_amount.grid(row=2, column=1, padx=5, pady=10)
    
    tk.Label(f_form, text="Type:", bg="#ecf0f1").grid(row=3, column=0, sticky="w")
    combo_type = ttk.Combobox(f_form, values=["Income", "Expense"])
    combo_type.current(0)
    combo_type.grid(row=3, column=1, padx=5, pady=5)
    
    tk.Label(f_form, text="Category:", bg="#ecf0f1").grid(row=4, column=0, sticky="w")
    combo_cat = ttk.Combobox(f_form, values=["Flexiload", "Sales", "Due Collection", "Bill", "Other"])
    combo_cat.current(1)
    combo_cat.grid(row=4, column=1, padx=5, pady=5)
    
    tk.Label(f_form, text="Method:", bg="#ecf0f1").grid(row=5, column=0, sticky="w")
    combo_method = ttk.Combobox(f_form, values=["Cash", "Due/Baki", "Bkash"])
    combo_method.current(0)
    combo_method.grid(row=5, column=1, padx=5, pady=5)
    
    tk.Button(f_form, text="SAVE", bg="green", fg="white", font=("Arial", 12, "bold"), width=20, command=save_transaction).grid(row=6, column=1, pady=20)

    # Customer UI
    tk.Label(frame_cust, text="Add New Customer", font=("Arial", 20, "bold"), bg="white").pack(pady=20)
    f_cform = tk.Frame(frame_cust, bg="#ecf0f1", padx=30, pady=30)
    f_cform.pack()
    
    tk.Label(f_cform, text="Name:", bg="#ecf0f1").grid(row=0, column=0)
    entry_new_name = tk.Entry(f_cform, width=30)
    entry_new_name.grid(row=0, column=1, pady=10)
    
    tk.Label(f_cform, text="Phone:", bg="#ecf0f1").grid(row=1, column=0)
    entry_new_phone = tk.Entry(f_cform, width=30)
    entry_new_phone.grid(row=1, column=1, pady=10)
    
    tk.Button(f_cform, text="SAVE CUSTOMER", bg="#2980b9", fg="white", command=add_new_customer).grid(row=2, column=1, pady=20)

    show_frame(frame_home)
    root.mainloop()

# ==========================================
# LOGIN SCREEN SETUP
# ==========================================
def show_login_screen():
    global login_window, entry_user, entry_pass
    login_window = tk.Tk()
    login_window.title("TeleCity Login")
    login_window.geometry("400x300")
    login_window.configure(bg="#2c3e50")

    tk.Label(login_window, text="USER LOGIN", font=("Arial", 18, "bold"), bg="#2c3e50", fg="white").pack(pady=30)

    f = tk.Frame(login_window, bg="#2c3e50")
    f.pack()

    tk.Label(f, text="Username:", bg="#2c3e50", fg="white").grid(row=0, column=0, padx=5, pady=5)
    entry_user = tk.Entry(f, width=25)
    entry_user.grid(row=0, column=1, padx=5, pady=5)

    tk.Label(f, text="Password:", bg="#2c3e50", fg="white").grid(row=1, column=0, padx=5, pady=5)
    entry_pass = tk.Entry(f, width=25, show="*")
    entry_pass.grid(row=1, column=1, padx=5, pady=5)

    tk.Button(login_window, text="LOGIN", bg="#27ae60", fg="white", font=("Arial", 10, "bold"), width=15, command=login).pack(pady=20)

    login_window.mainloop()

# এই লাইনটি খুব গুরুত্বপূর্ণ, হুবহু এরকম হতে হবে
if __name__ == "__main__":
    show_login_screen()