from tkinter import *
from tkinter import messagebox
from tkinter import ttk
import time
import os
import sys
import make_db_entry as db
import threading
import queue
import pyperclip


def check_singleton():
    if sys.platform == 'win32':
        if hasattr(sys, '_MEIPASS'):
            # we're in a pyinstaller environment, so use psutil to check for exe
            import psutil
            db_logger_exe_count = 0
            for proc in psutil.process_iter():
                try:
                    pinfo = proc.as_dict(attrs=['pid', 'name', 'username'])
                    if pinfo['name'] == 'db_logger_gui.exe':
                        db_logger_exe_count += 1
                        # print(pinfo['pid'], pinfo['name'])
                except psutil.NoSuchProcess:
                    pass
                else:
                    pass
            # When running the pyinstaller .exe, two processes are spawned, so
            # if we see more than that, we know there's already an instance
            # running
            if db_logger_exe_count > 2:
                raise OSError('Only one instance of db_logger_gui allowed')
        else:
            # we're not running as an .exe, so use tendo
            return tendo_singleton()
    elif sys.platform == 'linux':
        return tendo_singleton()


def tendo_singleton():
    from tendo import singleton
    try:
        me = singleton.SingleInstance()
    except singleton.SingleInstanceException as e:
        raise OSError('Only one instance of db_logger_gui allowed')
    return me


def resource_path(relative_path):
    try:
        # try to set the base_path to the pyinstaller temp dir (for when we're)
        # running from a compiled .exe built with pyinstaller
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath('.')

    pth = os.path.join(base_path, relative_path)

    return pth


def format_date(dt):
    """
    Format a datetime object in our preferred format

    Parameters
    ----------
    dt : datetime.datetime

    Returns
    -------
    datestring : str
        A datetime formatted in our preferred format
    """
    datestring = dt.strftime("%a %b %d, %Y\n%I:%M:%S %p")
    return datestring


class ScreenRes:
    def __init__(self):
        """
        When an instance of this class is created, the screen is queried for its
        dimensions. This is done once, so as to limit the number of calls to
        external programs.
        """
        default_screen_dims = ('800', '600')
        try:
            if sys.platform == 'win32':
                cmd = 'wmic path Win32_VideoController get ' + \
                      'CurrentHorizontalResolution, CurrentVerticalResolution'
                # Tested working in Windows XP and Windows 10
                screen_dims = tuple(
                    map(int, os.popen(cmd).read().split()[-2::]))
                print('INFO: Found "raw" Windows resolution of {}'.format(
                    screen_dims))

                # Get the DPI of the screen so we can adjust the resolution
                cmd = r'reg query "HKCU\Control Panel\Desktop\WindowMetrics" ' \
                      r'/v AppliedDPI'
                # pick off last value, which is DPI in hex, and convert to
                # decimal:
                try:
                    dpi = int(os.popen(cmd).read().split()[-1], 16)
                except Exception as e:
                    print('WARNING: DPI detection did not work with error: '
                          '{}'.format(e))
                    dpi = 96
                scale_factor = dpi / 96
                screen_dims = tuple(int(dim/scale_factor)
                                    for dim in screen_dims)
                print("INFO: Scale factor {}; Scaled ".format(scale_factor) +
                      "resolution is {}".format(screen_dims))

            elif sys.platform == 'linux':
                cmd = 'xrandr'
                screen_dims = os.popen(cmd).read()
                result = re.search(r'primary (\d+)x(\d+)', screen_dims)
                screen_dims = result.groups() if result else default_screen_dims
                screen_dims = tuple(map(int, screen_dims))
                print('INFO: Found Linux resolution of {}'.format(
                    screen_dims))
            else:
                screen_dims = default_screen_dims
        except Exception as e:
            print("WARNING: Caught exception when determining screen "
                  "resolution: {}".format(e))
            print("         Using default of {}".format(default_screen_dims))
            screen_dims = default_screen_dims
        self.screen_dims = screen_dims

    def get_center_geometry_string(self, width, height):
        """
        This method will return a Tkinter geometry string that will place a
        Toplevel
        window into the middle of the screen given the widget's width and
        height
        (using a Windows command or `xrandr` as needed). If it fails for some
        reason, a basic resolution of 800x600 is assumed.

        Parameters
        ----------
        width : int
            The width of the widget desired
        height : int
            The height of the widget desired

        Returns
        -------
        geometry_string : str
            The Tkinter geometry string that will put a window of `width` and
            `height` at the center of the screen given the current resolution
            (of
            the format "WIDTHxHEIGHT+XPOSITION+YPOSITION")
        """
        screen_width, screen_height = (int(x) for x in self.screen_dims)
        geometry_string = "%dx%d%+d%+d" % (width, height,
                                           int(screen_width / 2 - width / 2),
                                           int(screen_height / 2 - height / 2))
        return geometry_string


class MainApp(Tk):
    def __init__(self, screen_res=None):
        """
        This class configures and populates the main toplevel window. ``top`` is
        the toplevel containing window.

        Parameters
        ----------
        top : tkinter window
            The top level containing window
        screen_res : ScreenRes
            An instance of the screen resolution class to help determine where
            to place the window in the center of the screen
        """
        super(MainApp, self).__init__()
        testing = sys.platform != 'win32'
        print('INFO: Creating the session logger instance')
        self.db_logger = db.DBSessionLogger(verbosity=2,
                                            testing=testing,
                                            user=None if testing else
                                            os.environ['username'])
        self.startup_thread_queue = queue.Queue()
        # a separate queue that will contain either nothing, or an instruction
        # to exit (from the GUI to the make_db_entry code)
        self.startup_thread_exit_queue = queue.Queue()
        self.startup_thread = None
        self.end_thread_queue = queue.Queue()
        self.end_thread_exit_queue = queue.Queue()
        self.end_thread = None

        self.screen_res = ScreenRes() if screen_res is None else screen_res
        self.style = ttk.Style()
        if sys.platform == "win32":
            self.style.theme_use('winnative')
        self.style.configure('.', font="TkDefaultFont")

        self.tooltip_font = "TkDefaultFont"
        self.geometry(self.screen_res.get_center_geometry_string(350, 450))
        self.minsize(1, 1)
        self.maxsize(3840, 1170)
        self.resizable(0, 0)
        self.title("NexusLIMS Session Logger")
        self.configure(highlightcolor="black")

        # Set window icon
        self.icon = PhotoImage(master=self, file=resource_path("logo_bare.png"))
        self.wm_iconphoto(True, self.icon)

        # Top NexusLIMS logo with tooltip

        self.logo_img = PhotoImage(file=resource_path("logo_text_250x100.png"))
        self.logo_label = ttk.Label(self,
                                    background=self['background'],
                                    foreground="#000000",
                                    relief="flat",
                                    image=self.logo_img)
        ToolTip(self.logo_label,
                self.tooltip_font,
                'Brought to you by the NIST Office of Data and Informatics '
                'and the Electron Microscopy Nexus',
                delay=0.25)

        # Loading information that is hidden after session is established

        self.setup_frame = Frame(self)
        self.loading_Label = Label(self.setup_frame,
                                   anchor='center',
                                   justify='center',
                                   wraplength="250",
                                   text="Please wait while the session is "
                                        "established...")
        self.loading_pbar = ttk.Progressbar(self.setup_frame,
                                            orient=HORIZONTAL,
                                            length=200,
                                            mode='determinate')
        self.loading_status_text = StringVar()
        self.loading_status_text.set('Initiating session logger...')
        self.loading_status_Label = Label(self.setup_frame,
                                          foreground="#777",
                                          font='TkDefaultFont 8 italic',
                                          anchor='center',
                                          justify='center',
                                          wraplength="250",
                                          textvariable=self.loading_status_text)

        # Actual information that is shown once session is started
        self.running_frame = Frame(self)
        self.running_Label_1 = Label(self.running_frame,
                                     anchor='center',
                                     justify='center',
                                     wraplength="250",
                                     text="A new session has been started "
                                          "for the")
        self.instr_string = StringVar()
        self.instr_string.set("$INSTRUMENT")
        self.instrument_label = Label(self.running_frame,
                                      foreground="#12649b",
                                      anchor='center',
                                      justify='center',
                                      wraplength="250",
                                      textvariable=self.instr_string)
        self.running_Label_2 = Label(self.running_frame,
                                     anchor='center',
                                     justify='center',
                                     wraplength="250",
                                     text="at")
        self.datetime_string = StringVar()
        self.datetime_string.set('$DATETIME')
        self.datetime_label = Label(self.running_frame,
                                    foreground="#12649b",
                                    anchor='center',
                                    justify='center',
                                    wraplength="250",
                                    textvariable=self.datetime_string)
        self.running_Label_3 = Label(self.running_frame,
                                     anchor='center',
                                     justify='center',
                                     wraplength="250",
                                     text="Leave this window open while you "
                                          "work!"
                                          "\n\n"
                                          "To end the session (after all data "
                                          "has "
                                          "been saved to the network share), "
                                          "click "
                                          "the \"End session\" button below or "
                                          "close this window")

        # Buttons at bottom

        self.button_frame = Frame(self, padx=15, pady=10)
        self.end_icon = PhotoImage(file=resource_path('window-close.png'))
        self.end_button = Button(self.button_frame,
                                 # takefocus="",
                                 text="End session",
                                 padx=5, pady=5,
                                 state=DISABLED,
                                 compound=LEFT,
                                 command=self.session_end,
                                 image=self.end_icon)
        ToolTip(self.end_button,
                self.tooltip_font,
                "Ending the session will close this window and trigger a record"
                " of the session to be built (don't click unless you're sure "
                "you've saved all your data!)", delay=0.25)
        self.log_icon = PhotoImage(file=resource_path('file.png'))
        self.log_button = Button(self.button_frame,
                                 text="Show debug log",
                                 command=lambda: LogWindow(screen_res,
                                                           self.db_logger),
                                 padx=5, pady=5,
                                 compound=LEFT,
                                 image=self.log_icon)

        # grid the Toplevel window contents
        self.logo_label.grid(row=0, column=0, sticky=N, pady=(15, 0))

        # grid the setup_frame contents
        self.setup_frame.grid(row=1, column=0)
        self.loading_Label.grid(row=0, column=0)
        self.loading_pbar.grid(row=1, column=0, pady=10)
        self.loading_status_Label.grid(row=2, column=0)

        # grid the button_frame contents
        self.button_frame.grid(row=2, column=0, sticky=S, pady=(0, 15))
        self.end_button.grid(row=0, column=0, sticky=E, padx=15)
        self.log_button.grid(row=0, column=1, sticky=W, padx=15)

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.setup_frame.rowconfigure(0, weight=1)
        print('INFO: Created the top level window')

        self.session_startup()

    def session_startup(self):
        self.startup_thread = threading.Thread(
            target=self.session_startup_worker)
        self.startup_thread.start()
        self.after(100, self.watch_for_startup_result)

    def session_startup_worker(self):
        if self.db_logger.db_logger_setup(
                self.startup_thread_queue,
                self.startup_thread_exit_queue):
            if self.db_logger.last_session_ended(
                    self.startup_thread_queue,
                    self.startup_thread_exit_queue):
                if self.db_logger.process_start(
                        self.startup_thread_queue,
                        self.startup_thread_exit_queue):
                    self.db_logger.db_logger_teardown(
                        self.startup_thread_queue,
                        self.startup_thread_exit_queue)
            else:
                # we got an inconsistent state from the DB, so ask user
                # what to do about it
                response = HangingSessionDialog(self,
                                                screen_res=screen_res).show()
                print('Response is: {}'.format(response))

    def watch_for_startup_result(self):
        """
        Check if there is something in the queue
        """
        try:
            # print(list(self.startup_thread_queue.queue))
            res = self.startup_thread_queue.get(0)
            self.show_error_if_needed(res)
            # print('queue.res: {}'.format(res[0]))
            self.loading_status_text.set(res[0] +
                                         '...' if '!' not in res[0] else res[0])
            self.loading_pbar['value'] = int(res[1]/7.0 * 100)
            self.update()
            if res[0] == 'Unmounted network share':
                time.sleep(0.5)
                self.instr_string.set(self.db_logger.instr_schema_name)
                self.datetime_string.set(
                    format_date(self.db_logger.session_start_time))
                self.done_loading()
            else:
                self.after(100, self.watch_for_startup_result)
        except queue.Empty:
            self.after(100, self.watch_for_startup_result)

    def show_error_if_needed(self, res):
        if isinstance(res, Exception):
            self.loading_pbar['value'] = 50
            st = ttk.Style()
            st.configure("red.Horizontal.TProgressbar",
                         background='#990000')
            self.loading_pbar.configure(style="red.Horizontal.TProgressbar")
            messagebox.showerror(parent=self,
                                 title="Error",
                                 message="Error encountered during "
                                         "session setup: \n\n" +
                                         str(res))
            lw = LogWindow(screen_res, db_logger=self.db_logger,
                           is_error=True)
            lw.mainloop()

    def done_loading(self):
        # Remove the setup_frame contents
        self.setup_frame.grid_forget()

        # grid the running_frame contents to be shown after session is started
        self.running_frame.grid(row=1, column=0)
        self.running_Label_1.grid(row=0, pady=(20, 0))
        self.instrument_label.grid(row=1, pady=(15, 5))
        self.running_Label_2.grid(row=2, pady=(0, 0))
        self.datetime_label.grid(row=3, pady=(5, 15))
        self.running_Label_3.grid(row=4, pady=(0, 20))

        # activate the "end session" button
        self.end_button.configure(state=ACTIVE)

    def switch_gui_to_end(self):
        # Remove the setup_frame contents
        self.running_frame.grid_forget()

        # grid the setup_frame contents again
        self.setup_frame.grid(row=1, column=0)

        # deactivate the "end session" button
        self.end_button.configure(state=DISABLED)

    def session_end(self):
        # signal the startup thread to exit (if it's still running)
        self.startup_thread_exit_queue.put(True)
        # pass
        # do this in a separate end_thread (since it could take some time)
        if not self.db_logger.session_started:
            messagebox.showinfo("No session started",
                                "There was not a session started, so nothing "
                                "will be done. The logger will now exit.",
                                icon='warning')
            self.destroy()
        else:
            print('Starting session_end thread')
            self.end_thread = threading.Thread(target=self.session_end_worker)
            self.end_thread.start()
            self.loading_Label.configure(text="Please wait while the session "
                                              "end is logged to the "
                                              "database...\n(this window will "
                                              "close when completed)")
            self.switch_gui_to_end()
            self.loading_pbar['value'] = 0
            self.loading_status_text.set('Ending the session...')
            self.after(100, self.watch_for_end_result)

    def session_end_worker(self):
        if self.db_logger.db_logger_setup(self.end_thread_queue,
                                          self.end_thread_exit_queue):
            if self.db_logger.process_end(self.end_thread_queue,
                                          self.end_thread_exit_queue):
                self.db_logger.db_logger_teardown(self.end_thread_queue,
                                                  self.end_thread_exit_queue)

    def watch_for_end_result(self):
        """
        Check if there is something in the queue
        """
        try:
            # print(list(self.end_thread_queue.queue))
            res = self.end_thread_queue.get(0)
            self.show_error_if_needed(res)
            # print('queue.res: {}'.format(res[0]))
            self.loading_status_text.set(res[0] + '...')
            self.loading_pbar['value'] = int(res[1]/10.0 * 100)
            self.update()
            if res[0] == 'Unmounted network share':
                self.after(5000, self.destroy)
                self.close_warning(5)
                self.after(1000, lambda: self.close_warning(4))
                self.after(2000, lambda: self.close_warning(3))
                self.after(3000, lambda: self.close_warning(2))
                self.after(4000, lambda: self.close_warning(1))
                self.after(5000, lambda: self.close_warning(0))
            else:
                self.after(100, self.watch_for_end_result)
        except queue.Empty:
            self.after(100, self.watch_for_end_result)

    def close_warning(self, num_to_show):
        self.loading_status_text.set('Closing window in {} '
                                     'seconds...'.format(num_to_show))

    def on_closing(self):
        if messagebox.askokcancel("Confirm exit", "Are you sure you want to "
                                                  "exit? Any currently started "
                                                  "sessions will be ended.",
                                  icon='warning'):
            self.session_end()


class HangingSessionDialog(Toplevel):
    def __init__(self, parent, screen_res=None):
        self.response = StringVar()
        self.screen_res = ScreenRes() if screen_res is None else screen_res
        Toplevel.__init__(self, parent)
        self.geometry(self.screen_res.get_center_geometry_string(350, 175))
        self.grab_set()
        self.title("Incomplete session warning")
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        self.bell()

        self.new_icon = PhotoImage(file=resource_path('file-plus.png'))
        self.continue_icon = PhotoImage(file=resource_path(
            'arrow-alt-circle-right.png'))
        self.error_icon = PhotoImage(file=resource_path('error-icon.png'))

        self.top_frame = Frame(self)
        self.button_frame = Frame(self, padx=15, pady=10)
        self.label_frame = Frame(self.top_frame)

        self.top_label = Label(self.label_frame,
                               text="Warning!",
                               font=("TkDefaultFont", 12, "bold"),
                               wraplength=250,
                               anchor='w',
                               justify='left',
                               )
        self.warn_label = Label(self.label_frame,
                                wraplength=220,
                                anchor='w',
                                justify='left',
                                text="An interrupted session was "
                                     "found in the database for this "
                                     "instrument. Would you like to continue "
                                     "that existing session, or start a new "
                                     "one?")

        self.error_icon_label = ttk.Label(self.top_frame,
                                          background=self['background'],
                                          foreground="#000000",
                                          relief="flat",
                                          image=self.error_icon)

        self.continue_button = Button(self.button_frame,
                                      text='Continue',
                                      command=self.click_continue,
                                      padx=10, pady=5, width=80,
                                      compound=LEFT,
                                      image=self.continue_icon)
        self.new_button = Button(self.button_frame,
                                 text='New session',
                                 command=self.click_new,
                                 padx=10, pady=5, width=80,
                                 compound=LEFT,
                                 image=self.new_icon)

        self.top_frame.grid(row=0, column=0)
        self.error_icon_label.grid(column=0, row=0, padx=20, pady=25)
        self.label_frame.grid(column=1, row=0, padx=0, pady=0)
        self.top_label.grid(row=0, column=0, padx=10, pady=0, sticky=(W,S))
        self.warn_label.grid(row=1, column=0, padx=10, pady=(5,0))

        self.button_frame.grid(row=1, column=0,
                               sticky=S, ipadx=10, ipady=5)
        self.continue_button.grid(row=0, column=0, sticky=E, padx=15)
        self.new_button.grid(row=0, column=1, sticky=W, padx=15)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.focus_force()
        self.resizable(False, False)
        self.transient(parent)

    def show(self):
        self.wm_deiconify()
        self.focus_force()
        self.wait_window()
        return self.response.get()

    def click_new(self):
        self.response.set('new')
        self.destroy()

    def click_continue(self):
        self.response.set('continue')
        self.destroy()


class LogWindow(Toplevel):
    def __init__(self, screen_res=None, db_logger=None, is_error=False):
        """
        Create and raise a window showing a text field that holds the session
        logger `log_text`

        Parameters
        ----------
        screen_res : ScreenRes
            An instance of the screen resolution class to help determine where
            to place the window in the center of the screen
        db_logger : make_db_entry.DBSessionLogger
            The database logger, so we can access it's log_text
        is_error : bool
            If True, closing the log window will close the whole application
        """
        self.screen_res = ScreenRes() if screen_res is None else screen_res
        Toplevel.__init__(self, padx=3, pady=3)
        self.tooltip_font = "TkDefaultFont"
        self.geometry(self.screen_res.get_center_geometry_string(450, 350))
        self.title('NexusLIMS Session Logger Log')

        self.text_label = Label(self, text="Session Debugging Log:",
                                padx=5, pady=5)
        self.text = Text(self, width=40, height=10, wrap='none')
        self.text.insert('1.0',
                         "----------------------------------------------------"
                         "\n"
                         "If you encounter an error, please send the "
                         "following\n"
                         "log information to ***REMOVED*** for assistance \n"
                         "----------------------------------------------------"
                         "\n\n" +
                         db_logger.log_text)

        self.s_v = ttk.Scrollbar(self,
                                 orient=VERTICAL,
                                 command=self.text.yview)
        self.s_h = ttk.Scrollbar(self,
                                 orient=HORIZONTAL,
                                 command=self.text.xview)

        self.text['yscrollcommand'] = self.s_v.set
        self.text['xscrollcommand'] = self.s_h.set
        self.text.configure(state='disabled')

        self.button_frame = Frame(self, padx=15, pady=10)

        self.copy_icon = PhotoImage(file=resource_path('copy.png'))
        self.close_icon = PhotoImage(file=resource_path('window-close.png'))

        self.copy_button = Button(self.button_frame,
                                  text='Copy',  # log to clipboard',
                                  command=self.copy_text_to_clipboard,
                                  padx=10, pady=5, width=60,
                                  compound="left", image=self.copy_icon)
        ToolTip(self.copy_button,
                self.tooltip_font,
                "Copy log information to clipboard", delay=0.25)

        self.close_button = Button(self.button_frame,
                                   text='Close',  # window',
                                   command=self.destroy if not is_error else
                                   lambda: sys.exit(1),
                                   padx=10, pady=5, width=60,
                                   compound=LEFT, image=self.close_icon)
        ToolTip(self.close_button,
                self.tooltip_font,
                "Close this window" if not is_error else
                "Close the application; make sure to copy the log if you "
                "need!", delay=0.25)

        self.text_label.grid(column=0, row=0, sticky=(S, W))
        self.text.grid(column=0, row=1, sticky=(N, S, E, W))
        self.s_v.grid(column=1, row=1, sticky=(N, S))
        self.s_h.grid(column=0, row=2, sticky=(E, W))
        self.button_frame.grid(row=3, column=0, sticky=(S), ipadx=10)
        self.copy_button.grid(row=0, column=0, sticky=E, padx=10)
        self.close_button.grid(row=0, column=1, sticky=W, padx=10)

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.focus_force()
        if is_error:
            time_left = 5
            self.change_close_button(5, DISABLED)
            self.after(1000, lambda: self.change_close_button(4))
            self.after(2000, lambda: self.change_close_button(3))
            self.after(3000, lambda: self.change_close_button(2))
            self.after(4000, lambda: self.change_close_button(1))
            self.after(5000, lambda: self.change_close_button(0, ACTIVE))

    def change_close_button(self, num_to_show, state=DISABLED):
        if num_to_show == 0:
            self.close_button.configure(text='Close', state=state)
        else:
            self.close_button.configure(text='Close ({})'.format(
                num_to_show), state=state)
        self.close_button.grid(row=0, column=1, sticky=W, ipadx=10, padx=10)

    def copy_text_to_clipboard(self):
        text_content = self.text.get('1.0', 'end')
        self.clipboard_clear()
        if sys.platform == 'win32':
            text_content = text_content.replace('\n', '\r\n')
        pyperclip.copy(text_content)
        pyperclip.paste()
        self.update()


class ToolTip(Toplevel):
    """
    Provides a ToolTip widget for Tkinter.
    To apply a ToolTip to any Tkinter widget, simply pass the widget to the
    ToolTip constructor
    """

    def __init__(self, wdgt, tooltip_font, msg=None, msgFunc=None,
                 delay=1, follow=True):
        """
        Initialize the ToolTip

        Parameters
        ----------
        wdgt :
            The widget this ToolTip is assigned to
        tooltip_font : str
            Font to be used
        msg : str
            A static string message assigned to the ToolTip
        msgFunc : object
            A function that retrieves a string to use as the ToolTip text
        delay : float
            The delay in seconds before the ToolTip appears
        follow : bool
            If True, the ToolTip follows motion, otherwise hides
        """
        self.wdgt = wdgt
        # The parent of the ToolTip is the parent of the ToolTips widget
        self.parent = self.wdgt.master
        # Initialise the Toplevel
        Toplevel.__init__(self, self.parent, bg='black', padx=1, pady=1)
        # Hide initially
        self.withdraw()
        # The ToolTip Toplevel should have no frame or title bar
        self.overrideredirect(True)

        # The msgVar will contain the text displayed by the ToolTip
        self.msgVar = StringVar()
        if msg is None:
            self.msgVar.set('No message provided')
        else:
            self.msgVar.set(msg)
        self.msgFunc = msgFunc
        self.delay = delay
        self.follow = follow
        self.visible = 0
        self.lastMotion = 0
        # The text of the ToolTip is displayed in a Message widget
        Message(self, textvariable=self.msgVar, bg='#FFFFDD',
                font=tooltip_font, aspect=1000).grid()

        # Add bindings to the widget.  This will NOT override
        # bindings that the widget already has
        self.wdgt.bind('<Enter>', self.spawn, '+')
        self.wdgt.bind('<Leave>', self.hide, '+')
        self.wdgt.bind('<Motion>', self.move, '+')

    def spawn(self, event=None):
        """
        Spawn the ToolTip.  This simply makes the ToolTip eligible for display.
        Usually this is caused by entering the widget

        Arguments:
          event: The event that called this function
        """
        self.visible = 1
        # The after function takes a time argument in milliseconds
        self.after(int(self.delay * 1000), self.show)

    def show(self):
        """
        Displays the ToolTip if the time delay has been long enough
        """
        if self.visible == 1 and time.time() - self.lastMotion > self.delay:
            self.visible = 2
        if self.visible == 2:
            self.deiconify()

    def move(self, event):
        """
        Processes motion within the widget.
        Arguments:
          event: The event that called this function
        """
        self.lastMotion = time.time()
        # If the follow flag is not set, motion within the
        # widget will make the ToolTip disappear
        #
        if self.follow is False:
            self.withdraw()
            self.visible = 1

        # Offset the ToolTip 20x10 pixes southwest of the pointer
        self.geometry('+%i+%i' % (event.x_root + 20, event.y_root - 10))
        try:
            # Try to call the message function.  Will not change
            # the message if the message function is None or
            # the message function fails
            self.msgVar.set(self.msgFunc())
        except:
            pass
        self.after(int(self.delay * 1000), self.show)

    def hide(self, event=None):
        """
        Hides the ToolTip.  Usually this is caused by leaving the widget
        Arguments:
          event: The event that called this function
        """
        self.visible = 0
        self.withdraw()


if __name__ == "__main__":
    try:
        sing = check_singleton()
    except OSError as e:
        root = Tk()
        root.title('Error')
        message = "Only one instance of the NexusLIMS " + \
                  "Session Logger can be run at one time. " + \
                  "Please close the existing window if " + \
                  "you would like to start a new session " \
                  "and run the application again."
        if sys.platform == 'win32':
            message = message.replace('be run ', 'be run\n')
            message = message.replace('like to ', 'like to\n')
        root.withdraw()
        messagebox.showerror(parent=root,
                             title="Error",
                             message=message)
        sys.exit(0)

    screen_res = ScreenRes()
    root = MainApp(screen_res=screen_res)
    root.protocol("WM_DELETE_WINDOW", root.on_closing)
    root.mainloop()
