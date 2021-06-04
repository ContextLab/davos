# ADD DOCSTRING


class DotDict(dict):
    # ADD DOCSTRING
    # simple helper that allows a dict to be accessed like a JS object
    __delattr__ = dict.__delitem__
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__

    def __init__(self, d):
        # ADD DOCSTRING
        for k, v in d.items():
            if isinstance(v, dict):
                v = DotDict(v)
            self[k] = v


JS_FUNCTIONS = DotDict({
    'jupyter': {
        'restartRunCellsAbove': """\
            const restartRunCellsAbove = function() {
                const outputArea = this,
                    notebook = Jupyter.notebook,
                    // first cell currently selected, if multiple
                    anchorCellIndex = notebook.get_anchor_index(),
                    // most recently selected cell, if multiple
                    selectedCellIndex = notebook.get_selected_index(),
                    runningCell = outputArea.element.parents('.cell'),
                    allCells = notebook.get_cell_elements(),
                    runningCellIndex = allCells.index(runningCell);

                const queueCellsAndResetSelection = function() {
                    notebook.execute_cell_range(0, runningCellIndex + 1);
                    notebook.select(anchorCellIndex);
                    if (selectedCellIndex !== anchorCellIndex) {
                        // select multiple cells without moving anchor
                        notebook.select(selectedCellIndex, false);
                    }
                }

                notebook.kernel.restart(queueCellsAndResetSelection);
            }.bind(this)
        """,
        # TODO: don't forget to remove event listeners from all buttons
        'displayButtonPrompt': """\
            /**
             * Display one or more buttons for user selection and block until one is clicked
             * @param {Object[]} buttonArgs - Array of objects containing data for each 
             *     button/option to be displayed.
             * @param {String} [buttonArgs[].text=""] - Text label for the given button. 
             *     Defaults to an empty string.
             * @param {(BigInt|Boolean|null|Number|Object|String|undefined)} [buttonArgs[].result] - 
             *     Value assigned to the "result" trait of the ipywidgets object whose 
             *     model_id attribute is widgetModelId (if provided), if the given button is 
             *     clicked. Used to forward user input information to Python. JS types are 
             *     converted ty Python types, within reason (Boolean -> bool, Object -> dict, 
             *     null/undefined -> None, etc.). If omitted, the return value of onClick 
             *     will be used instead.
             * @param {Function} [buttonArgs[].onClick] - Callback run when the given button is 
             *     clicked, before the result value is set on the ipywidgets object and 
             *     Python execution resumes. Omit the result property to use the return value 
             *     of this function as a dynamically computed result value. 
             *     Defaults to a noop.
             * @param {String} [buttonArgs[].id] - Optional id for the given button element.
             * @param {String} [widgetModelId] - The ID of the ipywidgets WidgetModel object 
             *     whose "result" property will be assigned the result value for the clicked 
             *     button.
             */
            const displayButtonPrompt = async function(buttonArgs, widgetModelId) {
                let onClick, clickedButtonCallback, clickedButtonResult, resolutionFunc;
                const outputArea = this,
                    outputDisplayArea = element[0],
                    // store resolve function in outer scope so it can be called from an 
                    // event listener
                    callbackPromise = new Promise((resolve) => resolutionFunc = resolve );
                
                buttonArgs.forEach(function (buttonObj, ix) {
                    let buttonElement = document.createElement('BUTTON');
                    buttonElement.style.marginLeft = '1rem';
                    buttonElement.classList.add('davos', 'prompt-button');
                    if (typeof buttonObj.id !== 'undefined') {
                        buttonElement.id = buttonObj.id;
                    }
                    if (typeof buttonObj.text === 'undefined') {
                        buttonElement.textContent = '';
                    } else {
                        buttonElement.textContent = buttonObj.text;
                    }
                    if (typeof buttonObj.onClick === 'undefined') {
                        onClick = () => {};
                    } else {
                        onClick = buttonObj.onClick;
                    }
                    buttonElement.addEventListener('click', () => {
                        // store clicked button's callback & result, resolve awaited promise
                        clickedButtonCallback = onClick;
                        clickedButtonResult = buttonObj.result;
                        resolutionFunc();
                    });
                    outputDisplayArea.appendChild(buttonElement);
                })
                // attach handler to run when promise is fulfilled, pause until button is clicked
                await callbackPromise.then(() => {
                    // TODO: make sure this doesn't remove the widget model before we need it below
                    outputDisplayArea.remove();
                    const CbReturnVal = clickedButtonCallback();
                    
                    if (typeof widgetModelId !== 'undefined') {
                        if (typeof clickedButtonResult === 'undefined') {
                            clickedButtonResult = CbReturnVal;
                        }
                        const widgetManager = Jupyter.WidgetManager._managers[0],
                            widgetModel = widgetManager.get_model(widgetModelId);
                        widgetModel.then((model) => {
                            model.set('result', clickedButtonResult);
                            model.save_changes();
                        })
                    }
                })
            }.bind(this)
        """
    }
})
