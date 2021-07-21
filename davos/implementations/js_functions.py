# ADD DOCSTRING


__all__ = ['DotDict', 'JS_FUNCTIONS']


from textwrap import dedent


class DotDict(dict):
    # ADD DOCSTRING
    # simple helper that allows a dict to be accessed like a JS object
    __delattr__ = dict.__delitem__
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__

    # noinspection PyMissingConstructor
    def __init__(self, d):
        # ADD DOCSTRING
        for k, v in d.items():
            if isinstance(v, dict):
                v = DotDict(v)
            self[k] = v


# noinspection ThisExpressionReferencesGlobalObjectJS
# (expressions are passed to
# IPython.display.display(IPython.display.Javascript()), wherein `this`
# refers to the top-level output element for the cell from which it was
# invoked)
# noinspection JSUnusedLocalSymbols
# (accept JS functions defined but not called in language injection)
JS_FUNCTIONS = DotDict({
    'jupyter': {
        'restartRunCellsAbove': dedent("""\
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
                    /*
                     * Queue all cells above plus currently running cell. 
                     * Queueing cells unsets currently highlighted selected 
                     * cells, so re-select highlighted cell or group of cells/
                     */
                    // noinspection JSCheckFunctionSignatures
                    notebook.execute_cell_range(0, runningCellIndex + 1);
                    notebook.select(anchorCellIndex);
                    if (selectedCellIndex !== anchorCellIndex) {
                        // select multiple cells without moving anchor
                        notebook.select(selectedCellIndex, false);
                    }
                }
                // pass queueCellsAndResetSelection as callback to run after 
                // notebook kernel restarts and is available
                notebook.kernel.restart(queueCellsAndResetSelection);
            // when passed to Ipython.display.display(Ipython.display.Javascript()), 
            // "this" will be the [class=]"output" element of the cell from 
            // which it's displayed
            }.bind(this)
            """),
        # TODO: don't forget to remove event listeners from all buttons
        'displayButtonPrompt': dedent("""\
            /**
             * Display one or more buttons on the notebook frontend for user 
             * selection and (together with kernel-side Python function) block 
             * until one is clicked. Optionally send a per-button "result" 
             * value to the IPython kernel's stdin socket to capture user 
             * selection in a Python variable.
             * 
             * @param {Object[]} buttonArgs - Array of objects containing data 
             *     for each button to be displayed.
             * @param {String} [buttonArgs[].text=""] - Text label for the 
             *     given button. Defaults to an empty string.
             * @param {BigInt|Boolean|null|Number|Object|String|undefined} [buttonArgs[].result] - 
             *     Value sent to the notebook kernel's stdin socket if the 
             *     given button is clicked and sendResult is true. Used to 
             *     forward user input information to Python. JS types are 
             *     converted ty Python types, within reason (Boolean -> bool, 
             *     Object -> dict, Array -> list, null -> None, 
             *     undefined -> '', etc.). If omitted, the return value of 
             *     onClick will be used instead.
             * @param {Function} [buttonArgs[].onClick] - Callback executed 
             *     when the given button is clicked, before the result value is 
             *     sent to the IPython kernel and Python execution resumes. 
             *     Omit the result property to use this function's return value 
             *     as a dynamically computed result value. Defaults to a noop.
             * @param {String} [buttonArgs[].id] - Optional id for the given 
             *     button element.
             * @param {Boolean} [sendResult=false] - Whether to send the result 
             *     value to  the IPython kernel's stdin socket as simulated 
             *     user input.
             */
            const displayButtonPrompt = async function(buttonArgs, sendResult) {
                let clickedButtonCallback, clickedButtonResult, resolutionFunc;
                const outputDisplayArea = element[0],
                    // store resolve function in outer scope so it can be 
                    // called from an event listener
                    callbackPromise = new Promise((resolve) => resolutionFunc = resolve );
            
                buttonArgs.forEach(function (buttonObj, ix) {
                    let buttonElement = document.createElement('BUTTON');
                    buttonElement.style.marginLeft = '1rem';
                    buttonElement.classList.add('davos', 'prompt-button');
                    if (typeof buttonObj.id !== 'undefined') {
                        buttonElement.id = buttonObj.id;
                    }
                    if (typeof buttonObj.text === 'undefined') {
                        buttonElement.textContent = `Button ${ix}`;
                    } else {
                        buttonElement.textContent = buttonObj.text;
                    }
                    if (typeof buttonObj.onClick === 'undefined') {
                        // mutating object passed as argument isn't ideal, but 
                        // it's an easy way to make scoping in event listener 
                        // execution work, and should be pretty harmless since 
                        // this is internal use only
                        buttonObj.onClick = () => {};
                    }
                    buttonElement.addEventListener('click', () => {
                        // store clicked button's callback & result
                        clickedButtonCallback = buttonObj.onClick;
                        clickedButtonResult = buttonObj.result;
                        // resolve callbackPromise when any button is clicked
                        resolutionFunc();
                    });
                    outputDisplayArea.appendChild(buttonElement);
                })
                
                // attach handler to run when promise is fulfilled, await 
                // callbackPromise resolution (any button clicked)
                await callbackPromise.then(() => {
                    // remove element in output area containing buttons
                    outputDisplayArea.remove();
                    // execute clicked button's callback, store return value 
                    // (if any)
                    const CbReturnVal = clickedButtonCallback();
                    
                    if (sendResult === true) {
                        if (typeof clickedButtonResult === 'undefined') {
                            // if result should be sent to IPython kernel and 
                            // button's 'result' property was not specified, 
                            // use return value of button's onClick callback
                            clickedButtonResult = CbReturnVal;
                        }
                        // send result value to IPython kernel's stdin 
                        Jupyter.notebook.kernel.send_input_reply(clickedButtonResult);
                    }
                })
            // when passed to Ipython.display.display(Ipython.display.Javascript()), 
            // "this" will be the [class=]"output" element of the cell from 
            // which it's displayed
            }.bind(this);
        """)    # noqa: E124
    }
})
