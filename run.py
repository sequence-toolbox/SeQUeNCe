from sequence.gui.run_gui import run_gui

def run():
    app = run_gui().make_app()
    app.run_server(debug=False, host="127.0.0.1", port="8050")

if __name__ == '__main__':
    run()