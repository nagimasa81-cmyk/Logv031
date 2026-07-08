import json, os, sys, zipfile, shutil, datetime as dt, re
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext

APP_DIR = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent)) if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent
DATA_DIR = Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else APP_DIR
CONFIG_DIR = DATA_DIR / 'config'; MASTERS_DIR = DATA_DIR / 'masters'; TEMPLATES_DIR = DATA_DIR / 'templates'; PROFILES_DIR = DATA_DIR / 'profiles'; LOGS_DIR = DATA_DIR / 'logs'; RECORDS_DIR = DATA_DIR / 'records'
for p in [CONFIG_DIR, MASTERS_DIR, TEMPLATES_DIR, PROFILES_DIR, LOGS_DIR, RECORDS_DIR]: p.mkdir(parents=True, exist_ok=True)
NON_ENGLISH_RE = re.compile(r'[\u3040-\u30ff\u3400-\u9fff\uac00-\ud7af\u0e00-\u0e7f]')

FEATURES = {
    'complaint_tool': ('Complaint Tool', 'Create complaint, check English, generate mail/template.', '#0067d8'),
    'salesforce_auto_input': ('Salesforce Auto Input', 'Auto input to Salesforce on Microsoft Edge.', '#008a3d'),
    'update_master': ('Update Master', 'Load update ZIP. Backup is created automatically.', '#ef8a00'),
    'master_zip_builder': ('Master ZIP Builder', 'Edit masters and create update ZIP package.', '#6a35ad'),
    'settings': ('Settings', 'Default country, mode, language and paths.', '#008c9e'),
    'log_viewer': ('Log Viewer', 'View application logs and operation history.', '#1976d2'),
    'about': ('About', 'Application information and version.', '#0a3a68'),
}

LANGUAGES = {
    'en': 'English',
    'ja': '日本語',
    'ko': '한국어',
    'th': 'ไทย',
    'en-PH': 'English (PH)',
    'zh-TW': '繁體中文',
    'zh-CN': '简体中文'
}
COUNTRY_LANGUAGE = {
    'Japan': 'ja',
    'Korea': 'ko',
    'Thailand': 'th',
    'Philippines': 'en-PH',
    'Taiwan': 'zh-TW',
    'China': 'zh-CN',
    'India': 'en',
    'Australia': 'en',
    'Vietnam': 'en'
}
def default_language_for_company(company):
    countries = company.get('countries') or []
    if len(countries) == 1:
        return COUNTRY_LANGUAGE.get(countries[0], 'en')
    return company.get('default_language') or COUNTRY_LANGUAGE.get(countries[0], 'en') if countries else 'en'

def load_json(path, default):
    try:
        with open(path, 'r', encoding='utf-8') as f: return json.load(f)
    except Exception: return default

def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, indent=2)

def log_event(event, detail=''):
    with open(LOGS_DIR/'activity.log', 'a', encoding='utf-8') as f:
        f.write(f"{dt.datetime.now().isoformat(timespec='seconds')}\t{event}\t{detail}\n")

class Data:
    def __init__(self): self.reload()
    def reload(self):
        self.settings=load_json(CONFIG_DIR/'settings.json', {})
        self.users=load_json(CONFIG_DIR/'users.json', {'companies':[]})
        self.hospitals=load_json(MASTERS_DIR/'hospital_master.json', [])
        self.recipients=load_json(MASTERS_DIR/'recipients.json', {})
        self.fields=load_json(MASTERS_DIR/'field_definitions.json', {})
        self.templates=load_json(TEMPLATES_DIR/'email_template.json', {})
        self.translations=load_json(MASTERS_DIR/'translations.json', {'en': {}})
    def save_settings(self): save_json(CONFIG_DIR/'settings.json', self.settings)

class LoginDialog(tk.Toplevel):
    def __init__(self, master, data):
        super().__init__(master); self.data=data; self.result=None; self.title('Startup Selection'); self.geometry('560x440'); self.resizable(False,False); self.configure(bg='#f3f8fd'); self.grab_set()
        self.company_var=tk.StringVar(); self.password_var=tk.StringVar(); self.user_var=tk.StringVar(); self.actual_user_var=tk.StringVar()
        tk.Frame(self,bg='#083763',height=72).pack(fill='x')
        hdr=tk.Label(self,text='InSightec Complaint Service Hub',fg='white',bg='#083763',font=('Segoe UI',18,'bold')); hdr.place(x=24,y=18)
        body=ttk.Frame(self,padding=24); body.pack(fill='both',expand=True)
        ttk.Label(body,text='Company').grid(row=0,column=0,sticky='w',pady=8)
        self.company_cb=ttk.Combobox(body,textvariable=self.company_var,state='readonly',width=38,values=[c['display_name'] for c in data.users.get('companies',[])])
        self.company_cb.grid(row=0,column=1,sticky='ew',pady=8); self.company_cb.bind('<<ComboboxSelected>>', lambda e:self.on_company())
        ttk.Label(body,text='Password (InSightec only)').grid(row=1,column=0,sticky='w',pady=8)
        self.pw=ttk.Entry(body,textvariable=self.password_var,show='*',width=40); self.pw.grid(row=1,column=1,sticky='ew',pady=8)
        ttk.Label(body,text='User').grid(row=2,column=0,sticky='w',pady=8)
        self.user_cb=ttk.Combobox(body,textvariable=self.user_var,state='readonly',width=38); self.user_cb.grid(row=2,column=1,sticky='ew',pady=8)
        ttk.Label(body,text='Actual personal user\n(for shared users)').grid(row=3,column=0,sticky='w',pady=8)
        self.actual=ttk.Entry(body,textvariable=self.actual_user_var,width=40); self.actual.grid(row=3,column=1,sticky='ew',pady=8)
        info='Shared company users can log in, but Complaint input requires identifying the actual personal user before proceeding.'
        ttk.Label(body,text=info,wraplength=470,foreground='#345').grid(row=4,column=0,columnspan=2,sticky='w',pady=10)
        btns=ttk.Frame(body); btns.grid(row=5,column=0,columnspan=2,sticky='e',pady=18)
        ttk.Button(btns,text='Start',command=self.submit).pack(side='right',padx=4)
        ttk.Button(btns,text='Cancel',command=self.cancel).pack(side='right',padx=4)
        last=data.settings.get('last_company','InSightec'); self.company_var.set(last); self.on_company()
    def selected_company(self):
        return next((c for c in self.data.users.get('companies',[]) if c['display_name']==self.company_var.get()), None)
    def on_company(self):
        c=self.selected_company(); users=[u['name'] for u in (c or {}).get('users',[])]
        self.user_cb.configure(values=users); self.user_var.set(users[0] if users else '')
    def submit(self):
        c=self.selected_company()
        if not c: return messagebox.showerror('Required','Select company.')
        if c.get('requires_password') and self.password_var.get()!=c.get('password'):
            return messagebox.showerror('Password','Password is incorrect.')
        u=next((u for u in c.get('users',[]) if u['name']==self.user_var.get()), None)
        if not u: return messagebox.showerror('Required','Select user.')
        if u.get('role')=='shared' and not self.actual_user_var.get().strip():
            return messagebox.showerror('Required','Please enter actual personal user before proceeding.')
        self.result={'company':c,'user':u,'actual_user':self.actual_user_var.get().strip()}
        self.destroy()
    def cancel(self): self.result=None; self.destroy()

class Hub(tk.Tk):
    def __init__(self):
        super().__init__(); self.data=Data(); self.session=None; self.admin_mode=False
        self.title('InSightec Complaint Service Hub'); self.geometry('1260x820'); self.minsize(1120,720); self.configure(bg='#f6fbff')
        self.login(); self.language_var=tk.StringVar(value=self.current_language()); self.build()
    def current_language(self):
        if not self.session:
            return self.data.settings.get('default_language','en')
        if self.data.settings.get('language_mode') == 'manual':
            return self.data.settings.get('default_language','en')
        return default_language_for_company(self.session['company'])
    def tr(self, key, fallback=None):
        lang = getattr(self, 'language_var', tk.StringVar(value='en')).get()
        return self.data.translations.get(lang, self.data.translations.get('en', {})).get(key, fallback or key)
    def set_language(self, event=None):
        lang = self.language_var.get()
        self.data.settings['default_language'] = lang
        self.data.settings['language_mode'] = 'manual'
        self.data.save_settings()
        log_event('Language changed', lang)
        self.build()

    def login(self):
        dlg=LoginDialog(self,self.data); self.wait_window(dlg)
        if not dlg.result: self.destroy(); return
        self.session=dlg.result; self.data.settings['last_company']=self.session['company']['display_name']; self.data.settings['last_user']=self.session['user']['name']
        if self.data.settings.get('language_mode','auto') == 'auto':
            self.data.settings['default_language'] = default_language_for_company(self.session['company'])
        self.data.save_settings(); log_event('Login', f"{self.session['company']['display_name']} / {self.session['user']['name']}")
    def get_features(self):
        c=self.session['company']; u=self.session['user']
        if c['company_id']=='insightec' and u.get('admin_switch_allowed') and self.admin_mode:
            return c.get('features_admin', [])
        feats = list(c.get('features_user', []))
        if 'settings' not in feats: feats.append('settings')
        return feats
    def clear(self):
        for w in self.winfo_children(): w.destroy()
    def build(self):
        if not self.session: return
        self.clear()
        self.sidebar=tk.Frame(self,bg='#07355f',width=245); self.sidebar.pack(side='left',fill='y'); self.sidebar.pack_propagate(False)
        tk.Label(self.sidebar,text='InSightec',bg='#07355f',fg='white',font=('Segoe UI',30,'bold italic')).pack(anchor='w',padx=22,pady=(26,0))
        tk.Label(self.sidebar,text='Bringing therapy into focus',bg='#07355f',fg='white',font=('Segoe UI',10,'bold italic')).pack(anchor='w',padx=28,pady=(0,24))
        box=tk.Frame(self.sidebar,bg='#0b4a82',highlightbackground='#00a4ef',highlightthickness=1); box.pack(fill='x',padx=18,pady=12)
        tk.Label(box,text='Complaint Service Hub\nVer 0.3',justify='left',bg='#0b4a82',fg='white',font=('Segoe UI',12,'bold')).pack(anchor='w',padx=14,pady=12)
        for key in self.get_features():
            name=FEATURES[key][0]; b=tk.Button(self.sidebar,text='  '+name,anchor='w',relief='flat',bg='#07355f',fg='white',activebackground='#0c72ce',activeforeground='white',font=('Segoe UI',11),command=lambda k=key:self.open_feature(k)); b.pack(fill='x',padx=14,pady=3,ipady=7)
        tk.Label(self.sidebar,text='\nCompany: '+self.session['company']['display_name']+'\nUser: '+self.session['user']['name'],bg='#07355f',fg='#d7ecff',justify='left',font=('Segoe UI',9)).pack(side='bottom',anchor='w',padx=18,pady=18)
        self.main=tk.Frame(self,bg='#f6fbff'); self.main.pack(side='left',fill='both',expand=True)
        self.home()
    def header(self):
        h=tk.Frame(self.main,bg='#f6fbff'); h.pack(fill='x',padx=30,pady=(26,8))
        tk.Label(h,text='InSightec',fg='#005eb8',bg='#f6fbff',font=('Segoe UI',30,'bold')).pack(side='left')
        tk.Label(h,text=' Complaint Service Hub',fg='#1b1f2a',bg='#f6fbff',font=('Segoe UI',22,'bold')).pack(side='left',padx=10)
        if self.session['company']['company_id']=='insightec' and self.session['user'].get('admin_switch_allowed'):
            txt='Admin Mode: ON' if self.admin_mode else 'Admin Mode: OFF'
            tk.Button(h,text=txt,bg='#ffd24a' if self.admin_mode else 'white',fg='#07355f',command=self.toggle_admin).pack(side='right',padx=8,ipadx=12,ipady=8)
        tk.Label(h,text=dt.datetime.now().strftime('%Y-%m-%d  %H:%M'),fg='#07355f',bg='white',font=('Segoe UI',10,'bold'),relief='solid',bd=1,padx=18,pady=10).pack(side='right',padx=8)
        lang_box=ttk.Frame(h); lang_box.pack(side='right',padx=8)
        ttk.Label(lang_box,text='Language').pack(side='left',padx=(0,4))
        lang_cb=ttk.Combobox(lang_box,textvariable=self.language_var,state='readonly',width=10,values=list(LANGUAGES.keys()))
        lang_cb.pack(side='left'); lang_cb.bind('<<ComboboxSelected>>', self.set_language)
        tk.Label(self.main,text='All tools you need for Complaint management. Create, manage, and deliver with accuracy and speed.',bg='#f6fbff',fg='#223',font=('Segoe UI',12)).pack(anchor='w',padx=34)
        tk.Frame(self.main,bg='#b6d4ee',height=1).pack(fill='x',padx=30,pady=14)
    def home(self):
        for w in self.main.winfo_children(): w.destroy()
        self.header()
        grid=tk.Frame(self.main,bg='#f6fbff'); grid.pack(fill='both',expand=True,padx=28,pady=8)
        feats=self.get_features()
        for i,key in enumerate(feats): self.card(grid,key,i//3,i%3)
        foot=tk.Frame(self.main,bg='#07355f',height=48); foot.pack(fill='x',side='bottom'); tk.Label(foot,text='  ✓ Master Data: Loaded        Version: 0.3        Language: '+LANGUAGES.get(self.language_var.get(), self.language_var.get())+'',bg='#07355f',fg='white',font=('Segoe UI',10)).pack(side='left',pady=13)
    def card(self,parent,key,r,c):
        title,desc,color=FEATURES[key]
        f=tk.Frame(parent,bg='white',highlightbackground=color,highlightthickness=1); f.grid(row=r,column=c,sticky='nsew',padx=12,pady=12)
        parent.columnconfigure(c,weight=1); parent.rowconfigure(r,weight=1)
        tk.Label(f,text=title,bg='white',fg=color,font=('Segoe UI',15,'bold')).pack(anchor='w',padx=24,pady=(24,8))
        tk.Label(f,text=desc,bg='white',fg='#222',wraplength=260,justify='left',font=('Segoe UI',10)).pack(anchor='w',padx=24,pady=4)
        tk.Button(f,text='Start  ›',bg=color,fg='white',activebackground=color,activeforeground='white',font=('Segoe UI',11,'bold'),relief='flat',command=lambda:self.open_feature(key)).pack(fill='x',side='bottom',padx=22,pady=22,ipady=8)
    def toggle_admin(self): self.admin_mode=not self.admin_mode; self.build()
    def open_feature(self,key):
        if key=='complaint_tool': return ComplaintWindow(self,self.data,self.session)
        if key=='update_master': return self.update_master()
        if key=='salesforce_auto_input': return SalesforceWindow(self,self.session)
        if key=='master_zip_builder': return MasterBuilderWindow(self)
        if key=='log_viewer': return LogWindow(self)
        if key=='settings': return SettingsWindow(self,self.data,self.session,lambda: self.build())
        messagebox.showinfo(FEATURES[key][0], 'Prototype screen. Detailed function will be added in the next build.')
    def update_master(self):
        path=filedialog.askopenfilename(title='Select update ZIP',filetypes=[('ZIP','*.zip')])
        if not path: return
        backup=DATA_DIR/f"backup_{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}"; backup.mkdir(exist_ok=True)
        for d in ['config','masters','templates','profiles']:
            if (DATA_DIR/d).exists(): shutil.copytree(DATA_DIR/d, backup/d, dirs_exist_ok=True)
        try:
            with zipfile.ZipFile(path) as z: z.extractall(DATA_DIR)
            self.data.reload(); log_event('Master Updated', path); messagebox.showinfo('Update','Update completed. Backup was created.'); self.build()
        except Exception as e: messagebox.showerror('Update failed', str(e))

class ComplaintWindow(tk.Toplevel):
    def __init__(self,master,data,session):
        super().__init__(master); self.data=data; self.session=session; self.title('Complaint Tool'); self.geometry('950x720'); self.configure(bg='#f6fbff')
        default_country=data.settings.get('default_country') if data.settings.get('default_country') in session['company'].get('countries',[]) else (session['company'].get('countries') or ['India'])[0]
        self.country=tk.StringVar(value=default_country); self.hospital=tk.StringVar(); self.serial=tk.StringVar(); self.output=tk.StringVar(value=data.settings.get('default_output_mode','Copy Template'))
        frm=ttk.Frame(self,padding=14); frm.pack(fill='both',expand=True); frm.columnconfigure(1,weight=1); frm.rowconfigure(7,weight=1)
        ttk.Label(frm,text='Complaint Tool',font=('Segoe UI',18,'bold')).grid(row=0,column=0,columnspan=2,sticky='w',pady=8)
        self.combo(frm,1,'Country',self.country,session['company'].get('countries',[]),self.refresh_hospitals)
        self.hcb=self.combo(frm,2,'Hospital Name',self.hospital,[],self.on_hospital)
        self.scb=self.combo(frm,3,'System Serial',self.serial,[],self.on_serial)
        self.subject=tk.StringVar(); ttk.Label(frm,text='Subject').grid(row=4,column=0,sticky='w'); ttk.Entry(frm,textvariable=self.subject).grid(row=4,column=1,sticky='ew',pady=4)
        ttk.Label(frm,text='Description (English only)').grid(row=5,column=0,sticky='nw'); self.desc=scrolledtext.ScrolledText(frm,height=10,wrap='word'); self.desc.grid(row=5,column=1,sticky='nsew',pady=4)
        self.combo(frm,6,'Output Mode',self.output,['Outlook','Copy Template'],None)
        self.preview=scrolledtext.ScrolledText(frm,height=12,wrap='word'); self.preview.grid(row=7,column=0,columnspan=2,sticky='nsew',pady=8)
        btn=ttk.Frame(frm); btn.grid(row=8,column=0,columnspan=2,sticky='e')
        ttk.Button(btn,text='Generate Mail / Template',command=self.generate).pack(side='right',padx=4); ttk.Button(btn,text='Save Record',command=self.save).pack(side='right',padx=4)
        self.refresh_hospitals()
    def combo(self,p,r,l,v,vals,cmd):
        ttk.Label(p,text=l).grid(row=r,column=0,sticky='w',pady=4); cb=ttk.Combobox(p,textvariable=v,values=vals,state='normal'); cb.grid(row=r,column=1,sticky='ew',pady=4)
        if cmd: cb.bind('<<ComboboxSelected>>',lambda e:cmd())
        return cb
    def refresh_hospitals(self):
        hs=[h for h in self.data.hospitals if h.get('country')==self.country.get()]
        self.hcb.configure(values=[h.get('hospital_name','') for h in hs]); self.scb.configure(values=[h.get('system_serial','') for h in hs])
    def on_hospital(self):
        m=[h for h in self.data.hospitals if h.get('country')==self.country.get() and h.get('hospital_name')==self.hospital.get()]
        if len(m)==1: self.serial.set(m[0].get('system_serial',''))
    def on_serial(self):
        m=[h for h in self.data.hospitals if h.get('country')==self.country.get() and h.get('system_serial')==self.serial.get()]
        if len(m)==1: self.hospital.set(m[0].get('hospital_name',''))
    def values(self): return {'country':self.country.get(),'hospital':self.hospital.get(),'serial':self.serial.get(),'subject':self.subject.get(),'description':self.desc.get('1.0','end').strip(),'user':self.session['actual_user'] or self.session['user']['name'],'company':self.session['company']['display_name']}
    def generate(self):
        v=self.values(); txt=v['subject']+'\n'+v['description']
        if NON_ENGLISH_RE.search(txt): return messagebox.showerror('English check','Non-English characters were detected. Please write in English.')
        body=f"Complaint Subject: {v['subject']}\n\nDescription:\n{v['description']}\n\nCountry: {v['country']}\nHospital: {v['hospital']}\nSerial: {v['serial']}\nReporter: {v['user']}\nCompany: {v['company']}"
        self.preview.delete('1.0','end'); self.preview.insert('1.0',body); log_event('Complaint template generated', v['subject'])
        if self.output.get()=='Outlook': messagebox.showinfo('Outlook','Outlook creation is enabled in Windows build. Preview was generated here.')
    def save(self):
        v=self.values(); path=RECORDS_DIR/f"complaint_{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"; save_json(path,v); messagebox.showinfo('Saved',str(path)); log_event('Record saved',str(path))

class SalesforceWindow(tk.Toplevel):
    def __init__(self,master,session):
        super().__init__(master); self.title('Salesforce Auto Input'); self.geometry('720x420')
        txt='Open Salesforce in Microsoft Edge, open the input form, click anywhere inside the editable form, then this tool will input all mapped fields. Submit/Save is not clicked automatically.'
        ttk.Label(self,text='Salesforce Auto Input',font=('Segoe UI',18,'bold')).pack(anchor='w',padx=18,pady=18); ttk.Label(self,text=txt,wraplength=650).pack(anchor='w',padx=18); ttk.Button(self,text='Start Auto Input Prototype',command=lambda:messagebox.showinfo('Prototype','Auto input engine placeholder. Screenshot-based mapping will be added after Salesforce screenshots are provided.')).pack(pady=30)
class MasterBuilderWindow(tk.Toplevel):
    def __init__(self,master): super().__init__(master); self.title('Master ZIP Builder'); self.geometry('650x380'); ttk.Label(self,text='Master ZIP Builder',font=('Segoe UI',18,'bold')).pack(padx=18,pady=18); ttk.Button(self,text='Create Update ZIP from current config/masters/templates/profiles',command=self.make_zip).pack(pady=20)
    def make_zip(self):
        out=DATA_DIR/f"master_update_{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
            for d in ['config','masters','templates','profiles']:
                for p in (DATA_DIR/d).rglob('*'):
                    if p.is_file(): z.write(p,p.relative_to(DATA_DIR))
        messagebox.showinfo('Created',str(out))
class LogWindow(tk.Toplevel):
    def __init__(self,master): super().__init__(master); self.title('Log Viewer'); self.geometry('800x500'); t=scrolledtext.ScrolledText(self); t.pack(fill='both',expand=True); t.insert('1.0',(LOGS_DIR/'activity.log').read_text(encoding='utf-8') if (LOGS_DIR/'activity.log').exists() else '')
class SettingsWindow(tk.Toplevel):
    def __init__(self,master,data,session,on_saved=None):
        super().__init__(master); self.data=data; self.session=session; self.on_saved=on_saved
        self.title('Settings'); self.geometry('720x460'); self.configure(bg='#f6fbff')
        self.lang_mode=tk.StringVar(value=data.settings.get('language_mode','auto'))
        self.lang=tk.StringVar(value=data.settings.get('default_language', default_language_for_company(session['company'])))
        self.country=tk.StringVar(value=data.settings.get('default_country', (session['company'].get('countries') or [''])[0]))
        self.output=tk.StringVar(value=data.settings.get('default_output_mode','Copy Template'))
        frm=ttk.Frame(self,padding=24); frm.pack(fill='both',expand=True); frm.columnconfigure(1,weight=1)
        ttk.Label(frm,text='Settings',font=('Segoe UI',18,'bold')).grid(row=0,column=0,columnspan=2,sticky='w',pady=(0,18))
        ttk.Label(frm,text='Language Mode').grid(row=1,column=0,sticky='w',pady=8)
        ttk.Combobox(frm,textvariable=self.lang_mode,state='readonly',values=['auto','manual']).grid(row=1,column=1,sticky='ew',pady=8)
        ttk.Label(frm,text='UI Language').grid(row=2,column=0,sticky='w',pady=8)
        ttk.Combobox(frm,textvariable=self.lang,state='readonly',values=list(LANGUAGES.keys())).grid(row=2,column=1,sticky='ew',pady=8)
        ttk.Label(frm,text='Default Country').grid(row=3,column=0,sticky='w',pady=8)
        ttk.Combobox(frm,textvariable=self.country,state='readonly',values=session['company'].get('countries',[])).grid(row=3,column=1,sticky='ew',pady=8)
        ttk.Label(frm,text='Default Output Mode').grid(row=4,column=0,sticky='w',pady=8)
        ttk.Combobox(frm,textvariable=self.output,state='readonly',values=['Outlook','Copy Template']).grid(row=4,column=1,sticky='ew',pady=8)
        info='Auto language uses company/country default. You can switch language anytime from the top dropdown or set manual language here.'
        ttk.Label(frm,text=info,wraplength=620,foreground='#345').grid(row=5,column=0,columnspan=2,sticky='w',pady=18)
        ttk.Button(frm,text='Save Settings',command=self.save).grid(row=6,column=1,sticky='e',pady=18)
    def save(self):
        self.data.settings['language_mode']=self.lang_mode.get()
        self.data.settings['default_language']=self.lang.get()
        self.data.settings['default_country']=self.country.get()
        self.data.settings['default_output_mode']=self.output.get()
        self.data.save_settings(); log_event('Settings saved', self.lang.get())
        messagebox.showinfo('Settings','Settings saved.')
        if self.on_saved: self.on_saved()
        self.destroy()

if __name__=='__main__':
    Hub().mainloop()
