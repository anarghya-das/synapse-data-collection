/**************** 
 * Hearing *
 ****************/

import { core, data, sound, util, visual, hardware } from './lib/psychojs-2024.2.4.js';
const { PsychoJS } = core;
const { TrialHandler, MultiStairHandler } = data;
const { Scheduler } = util;
//some handy aliases as in the psychopy scripts;
const { abs, sin, cos, PI: pi, sqrt } = Math;
const { round } = util;


// store info about the experiment session:
let expName = 'hearing';  // from the Builder filename that created this script
let expInfo = {
    'participant': `${util.pad(Number.parseFloat(util.randint(0, 999999)).toFixed(0), 6)}`,
    'run': '1',
    'config': 'hearing',
    'enable_video': 'true',
    'enable_ppg': 'false',
};

// Start code blocks for 'Before Experiment'
// init psychoJS:
const psychoJS = new PsychoJS({
  debug: true
});

// open window:
psychoJS.openWindow({
  fullscr: true,
  color: new util.Color([(- 1.0), (- 1.0), (- 1.0)]),
  units: 'height',
  waitBlanking: true,
  backgroundImage: '',
  backgroundFit: 'none',
});
// schedule the experiment:
psychoJS.schedule(psychoJS.gui.DlgFromDict({
  dictionary: expInfo,
  title: expName
}));

const flowScheduler = new Scheduler(psychoJS);
const dialogCancelScheduler = new Scheduler(psychoJS);
psychoJS.scheduleCondition(function() { return (psychoJS.gui.dialogComponent.button === 'OK'); },flowScheduler, dialogCancelScheduler);

// flowScheduler gets run if the participants presses OK
flowScheduler.add(updateInfo); // add timeStamp
flowScheduler.add(experimentInit);
flowScheduler.add(welcomeRoutineBegin());
flowScheduler.add(welcomeRoutineEachFrame());
flowScheduler.add(welcomeRoutineEnd());
const trials_pmtLoopScheduler = new Scheduler(psychoJS);
flowScheduler.add(trials_pmtLoopBegin(trials_pmtLoopScheduler));
flowScheduler.add(trials_pmtLoopScheduler);
flowScheduler.add(trials_pmtLoopEnd);




flowScheduler.add(hlt_welcomeRoutineBegin());
flowScheduler.add(hlt_welcomeRoutineEachFrame());
flowScheduler.add(hlt_welcomeRoutineEnd());
const trials_hltLoopScheduler = new Scheduler(psychoJS);
flowScheduler.add(trials_hltLoopBegin(trials_hltLoopScheduler));
flowScheduler.add(trials_hltLoopScheduler);
flowScheduler.add(trials_hltLoopEnd);





flowScheduler.add(let_welcomeRoutineBegin());
flowScheduler.add(let_welcomeRoutineEachFrame());
flowScheduler.add(let_welcomeRoutineEnd());
const trials_letLoopScheduler = new Scheduler(psychoJS);
flowScheduler.add(trials_letLoopBegin(trials_letLoopScheduler));
flowScheduler.add(trials_letLoopScheduler);
flowScheduler.add(trials_letLoopEnd);





flowScheduler.add(ast_welcomeRoutineBegin());
flowScheduler.add(ast_welcomeRoutineEachFrame());
flowScheduler.add(ast_welcomeRoutineEnd());
const trials_astLoopScheduler = new Scheduler(psychoJS);
flowScheduler.add(trials_astLoopBegin(trials_astLoopScheduler));
flowScheduler.add(trials_astLoopScheduler);
flowScheduler.add(trials_astLoopEnd);




flowScheduler.add(end_2RoutineBegin());
flowScheduler.add(end_2RoutineEachFrame());
flowScheduler.add(end_2RoutineEnd());
flowScheduler.add(quitPsychoJS, '', true);

// quit if user presses Cancel in dialog box:
dialogCancelScheduler.add(quitPsychoJS, '', false);

psychoJS.start({
  expName: expName,
  expInfo: expInfo,
  resources: [
    // resources:
  ]
});

psychoJS.experimentLogger.setLevel(core.Logger.ServerLevel.EXP);

async function updateInfo() {
  currentLoop = psychoJS.experiment;  // right now there are no loops
  expInfo['date'] = util.MonotonicClock.getDateStr();  // add a simple timestamp
  expInfo['expName'] = expName;
  expInfo['psychopyVersion'] = '2024.2.4';
  expInfo['OS'] = window.navigator.platform;


  // store frame rate of monitor if we can measure it successfully
  expInfo['frameRate'] = psychoJS.window.getActualFrameRate();
  if (typeof expInfo['frameRate'] !== 'undefined')
    frameDur = 1.0 / Math.round(expInfo['frameRate']);
  else
    frameDur = 1.0 / 60.0; // couldn't get a reliable measure so guess

  // add info from the URL:
  util.addInfoFromUrl(expInfo);
  

  
  psychoJS.experiment.dataFileName = (("." + "/") + `data/${expInfo["participant"]}/${expInfo["participant"]}_${expName}_${expInfo["date"]}`);
  psychoJS.experiment.field_separator = '\t';


  return Scheduler.Event.NEXT;
}

async function experimentInit() {
  // Initialize components for Routine "welcome"
  welcomeClock = new util.Clock();
  text_2 = new visual.TextStim({
    win: psychoJS.window,
    name: 'text_2',
    text: 'Welcome!\n\nPlease focus only on the cross area on the screen.\n\nUse your right hand to hold the mouse, as you will need it shortly.\n\nIn experiment 1, the screen color will change. No response is required from you.\n\nWhen you are ready, click the left mouse button to start the experiment.\n',
    font: 'Open Sans',
    units: undefined, 
    pos: [0, 0], draggable: false, height: 0.05,  wrapWidth: undefined, ori: 0.0,
    languageStyle: 'LTR',
    color: new util.Color('white'),  opacity: undefined,
    depth: -1.0 
  });
  
  mouse = new core.Mouse({
    win: psychoJS.window,
  });
  mouse.mouseClock = new util.Clock();
  // Initialize components for Routine "pmt_prestim"
  pmt_prestimClock = new util.Clock();
  black_screen = new visual.Rect ({
    win: psychoJS.window, name: 'black_screen', 
    width: [2, 1][0], height: [2, 1][1],
    ori: 0.0, 
    pos: [0, 0], 
    draggable: false, 
    anchor: 'center', 
    lineWidth: 1.0, 
    lineColor: new util.Color([(- 1.0), (- 1.0), (- 1.0)]), 
    fillColor: new util.Color([(- 1.0), (- 1.0), (- 1.0)]), 
    colorSpace: 'rgb', 
    opacity: undefined, 
    depth: -1, 
    interpolate: true, 
  });
  
  cross_7 = new visual.ShapeStim ({
    win: psychoJS.window, name: 'cross_7', 
    vertices: 'cross', size:[0.3, 0.3],
    ori: 0.0, 
    pos: [0, 0], 
    draggable: false, 
    anchor: 'center', 
    lineWidth: 1.0, 
    lineColor: new util.Color('white'), 
    fillColor: new util.Color('white'), 
    colorSpace: 'rgb', 
    opacity: undefined, 
    depth: -2, 
    interpolate: true, 
  });
  
  // Initialize components for Routine "pmt_stim"
  pmt_stimClock = new util.Clock();
  marker_outlet.push_sample(["pmt_stim"]);
  
  gray_screen = new visual.Rect ({
    win: psychoJS.window, name: 'gray_screen', 
    width: [2, 1][0], height: [2, 1][1],
    ori: 0.0, 
    pos: [0, 0], 
    draggable: false, 
    anchor: 'center', 
    lineWidth: 1.0, 
    lineColor: new util.Color([0.0039, 0.0039, 0.0039]), 
    fillColor: new util.Color([0.0039, 0.0039, 0.0039]), 
    colorSpace: 'rgb', 
    opacity: undefined, 
    depth: -1, 
    interpolate: true, 
  });
  
  cross_8 = new visual.ShapeStim ({
    win: psychoJS.window, name: 'cross_8', 
    vertices: 'cross', size:[0.3, 0.3],
    ori: 0.0, 
    pos: [0, 0], 
    draggable: false, 
    anchor: 'center', 
    lineWidth: 1.0, 
    lineColor: new util.Color('white'), 
    fillColor: new util.Color('white'), 
    colorSpace: 'rgb', 
    opacity: undefined, 
    depth: -2, 
    interpolate: true, 
  });
  
  // Initialize components for Routine "pmt_poststim"
  pmt_poststimClock = new util.Clock();
  marker_outlet.push_sample(["pmt_poststim"]);
  
  black_screen_2 = new visual.Rect ({
    win: psychoJS.window, name: 'black_screen_2', 
    width: [2, 1][0], height: [2, 1][1],
    ori: 0.0, 
    pos: [0, 0], 
    draggable: false, 
    anchor: 'center', 
    lineWidth: 1.0, 
    lineColor: new util.Color([(- 1.0), (- 1.0), (- 1.0)]), 
    fillColor: new util.Color([(- 1.0), (- 1.0), (- 1.0)]), 
    colorSpace: 'rgb', 
    opacity: undefined, 
    depth: -1, 
    interpolate: true, 
  });
  
  cross_9 = new visual.ShapeStim ({
    win: psychoJS.window, name: 'cross_9', 
    vertices: 'cross', size:[0.3, 0.3],
    ori: 0.0, 
    pos: [0, 0], 
    draggable: false, 
    anchor: 'center', 
    lineWidth: 1.0, 
    lineColor: new util.Color('white'), 
    fillColor: new util.Color('white'), 
    colorSpace: 'rgb', 
    opacity: undefined, 
    depth: -2, 
    interpolate: true, 
  });
  
  // Initialize components for Routine "hlt_welcome"
  hlt_welcomeClock = new util.Clock();
  text = new visual.TextStim({
    win: psychoJS.window,
    name: 'text',
    text: "In Experiment 2, \n\nWe will play a pure-tone sound, gradually increasing the loudness.\n\nFor each loudness level, please rate it as follows:\n\n0: Can't hear\n1: Clearly audible\n2: Too loud\n\nUse the left mouse button to select your rating. When you are ready, click the left mouse button to start.",
    font: 'Open Sans',
    units: undefined, 
    pos: [0, 0], draggable: false, height: 0.05,  wrapWidth: undefined, ori: 0.0,
    languageStyle: 'LTR',
    color: new util.Color('white'),  opacity: undefined,
    depth: 0.0 
  });
  
  mouse_2 = new core.Mouse({
    win: psychoJS.window,
  });
  mouse_2.mouseClock = new util.Clock();
  // Initialize components for Routine "hlt_prestim"
  hlt_prestimClock = new util.Clock();
  black_screen_3 = new visual.Rect ({
    win: psychoJS.window, name: 'black_screen_3', 
    width: [2, 1][0], height: [2, 1][1],
    ori: 0.0, 
    pos: [0, 0], 
    draggable: false, 
    anchor: 'center', 
    lineWidth: 1.0, 
    lineColor: new util.Color([(- 1.0), (- 1.0), (- 1.0)]), 
    fillColor: new util.Color([(- 1.0), (- 1.0), (- 1.0)]), 
    colorSpace: 'rgb', 
    opacity: undefined, 
    depth: -1, 
    interpolate: true, 
  });
  
  cross_2 = new visual.ShapeStim ({
    win: psychoJS.window, name: 'cross_2', 
    vertices: 'cross', size:[0.3, 0.3],
    ori: 0.0, 
    pos: [0, 0], 
    draggable: false, 
    anchor: 'center', 
    lineWidth: 1.0, 
    lineColor: new util.Color('white'), 
    fillColor: new util.Color('white'), 
    colorSpace: 'rgb', 
    opacity: undefined, 
    depth: -2, 
    interpolate: true, 
  });
  
  // Initialize components for Routine "hlt_stim"
  hlt_stimClock = new util.Clock();
  hlt_sound = new sound.Sound({
      win: psychoJS.window,
      value: 'A',
      secs: (- 1),
      });
  hlt_sound.setVolume(1.0);
  black_screen_4 = new visual.Rect ({
    win: psychoJS.window, name: 'black_screen_4', 
    width: [2, 1][0], height: [2, 1][1],
    ori: 0.0, 
    pos: [0, 0], 
    draggable: false, 
    anchor: 'center', 
    lineWidth: 1.0, 
    lineColor: new util.Color([(- 1.0), (- 1.0), (- 1.0)]), 
    fillColor: new util.Color([(- 1.0), (- 1.0), (- 1.0)]), 
    colorSpace: 'rgb', 
    opacity: undefined, 
    depth: -2, 
    interpolate: true, 
  });
  
  cross_5 = new visual.ShapeStim ({
    win: psychoJS.window, name: 'cross_5', 
    vertices: 'cross', size:[0.3, 0.3],
    ori: 0.0, 
    pos: [0, 0], 
    draggable: false, 
    anchor: 'center', 
    lineWidth: 1.0, 
    lineColor: new util.Color('white'), 
    fillColor: new util.Color('white'), 
    colorSpace: 'rgb', 
    opacity: undefined, 
    depth: -3, 
    interpolate: true, 
  });
  
  // Initialize components for Routine "hlt_poststim"
  hlt_poststimClock = new util.Clock();
  black_screen_5 = new visual.Rect ({
    win: psychoJS.window, name: 'black_screen_5', 
    width: [2, 1][0], height: [2, 1][1],
    ori: 0.0, 
    pos: [0, 0], 
    draggable: false, 
    anchor: 'center', 
    lineWidth: 1.0, 
    lineColor: new util.Color([(- 1.0), (- 1.0), (- 1.0)]), 
    fillColor: new util.Color([(- 1.0), (- 1.0), (- 1.0)]), 
    colorSpace: 'rgb', 
    opacity: undefined, 
    depth: -1, 
    interpolate: true, 
  });
  
  cross_6 = new visual.ShapeStim ({
    win: psychoJS.window, name: 'cross_6', 
    vertices: 'cross', size:[0.3, 0.3],
    ori: 0.0, 
    pos: [0, 0], 
    draggable: false, 
    anchor: 'center', 
    lineWidth: 1.0, 
    lineColor: new util.Color('white'), 
    fillColor: new util.Color('white'), 
    colorSpace: 'rgb', 
    opacity: undefined, 
    depth: -2, 
    interpolate: true, 
  });
  
  // Initialize components for Routine "hlt_response"
  hlt_responseClock = new util.Clock();
  slider_4 = new visual.Slider({
    win: psychoJS.window, name: 'slider_4',
    startValue: undefined,
    size: [1.0, 0.1], pos: [0, 0], ori: 0.0, units: psychoJS.window.units,
    labels: [0, 1, 2], fontSize: 0.05, ticks: [],
    granularity: 1, style: ["RADIO"],
    color: new util.Color('LightGray'), markerColor: new util.Color('Red'), lineColor: new util.Color('White'), 
    opacity: undefined, fontFamily: 'Open Sans', bold: true, italic: false, depth: -1, 
    flip: false,
  });
  
  // Initialize components for Routine "let_welcome"
  let_welcomeClock = new util.Clock();
  text_6 = new visual.TextStim({
    win: psychoJS.window,
    name: 'text_6',
    text: 'In Experiment 3, \n\nA voice will speak random numbers from 0 to 20.\n\nEach time you hear a number, click the left mouse button to select the corresponding number on the screen. \n\nWhen you are ready, click the left mouse button to start',
    font: 'Open Sans',
    units: undefined, 
    pos: [0, 0], draggable: false, height: 0.05,  wrapWidth: undefined, ori: 0.0,
    languageStyle: 'LTR',
    color: new util.Color('white'),  opacity: undefined,
    depth: 0.0 
  });
  
  mouse_3 = new core.Mouse({
    win: psychoJS.window,
  });
  mouse_3.mouseClock = new util.Clock();
  // Initialize components for Routine "let_prestim"
  let_prestimClock = new util.Clock();
  black_screen_6 = new visual.Rect ({
    win: psychoJS.window, name: 'black_screen_6', 
    width: [2, 1][0], height: [2, 1][1],
    ori: 0.0, 
    pos: [0, 0], 
    draggable: false, 
    anchor: 'center', 
    lineWidth: 1.0, 
    lineColor: new util.Color([(- 1.0), (- 1.0), (- 1.0)]), 
    fillColor: new util.Color([(- 1.0), (- 1.0), (- 1.0)]), 
    colorSpace: 'rgb', 
    opacity: undefined, 
    depth: -1, 
    interpolate: true, 
  });
  
  cross_10 = new visual.ShapeStim ({
    win: psychoJS.window, name: 'cross_10', 
    vertices: 'cross', size:[0.3, 0.3],
    ori: 0.0, 
    pos: [0, 0], 
    draggable: false, 
    anchor: 'center', 
    lineWidth: 1.0, 
    lineColor: new util.Color('white'), 
    fillColor: new util.Color('white'), 
    colorSpace: 'rgb', 
    opacity: undefined, 
    depth: -2, 
    interpolate: true, 
  });
  
  // Initialize components for Routine "let_stim"
  let_stimClock = new util.Clock();
  let_sound = new sound.Sound({
      win: psychoJS.window,
      value: 'A',
      secs: (- 1),
      });
  let_sound.setVolume(1.0);
  black_screen_7 = new visual.Rect ({
    win: psychoJS.window, name: 'black_screen_7', 
    width: [2, 1][0], height: [2, 1][1],
    ori: 0.0, 
    pos: [0, 0], 
    draggable: false, 
    anchor: 'center', 
    lineWidth: 1.0, 
    lineColor: new util.Color([(- 1.0), (- 1.0), (- 1.0)]), 
    fillColor: new util.Color([(- 1.0), (- 1.0), (- 1.0)]), 
    colorSpace: 'rgb', 
    opacity: undefined, 
    depth: -2, 
    interpolate: true, 
  });
  
  cross_11 = new visual.ShapeStim ({
    win: psychoJS.window, name: 'cross_11', 
    vertices: 'cross', size:[0.3, 0.3],
    ori: 0.0, 
    pos: [0, 0], 
    draggable: false, 
    anchor: 'center', 
    lineWidth: 1.0, 
    lineColor: new util.Color('white'), 
    fillColor: new util.Color('white'), 
    colorSpace: 'rgb', 
    opacity: undefined, 
    depth: -3, 
    interpolate: true, 
  });
  
  // Initialize components for Routine "let_poststim"
  let_poststimClock = new util.Clock();
  black_screen_8 = new visual.Rect ({
    win: psychoJS.window, name: 'black_screen_8', 
    width: [2, 1][0], height: [2, 1][1],
    ori: 0.0, 
    pos: [0, 0], 
    draggable: false, 
    anchor: 'center', 
    lineWidth: 1.0, 
    lineColor: new util.Color([(- 1.0), (- 1.0), (- 1.0)]), 
    fillColor: new util.Color([(- 1.0), (- 1.0), (- 1.0)]), 
    colorSpace: 'rgb', 
    opacity: undefined, 
    depth: -1, 
    interpolate: true, 
  });
  
  cross_12 = new visual.ShapeStim ({
    win: psychoJS.window, name: 'cross_12', 
    vertices: 'cross', size:[0.3, 0.3],
    ori: 0.0, 
    pos: [0, 0], 
    draggable: false, 
    anchor: 'center', 
    lineWidth: 1.0, 
    lineColor: new util.Color('white'), 
    fillColor: new util.Color('white'), 
    colorSpace: 'rgb', 
    opacity: undefined, 
    depth: -2, 
    interpolate: true, 
  });
  
  // Initialize components for Routine "let_response"
  let_responseClock = new util.Clock();
  slider_5 = new visual.Slider({
    win: psychoJS.window, name: 'slider_5',
    startValue: undefined,
    size: [1.0, 0.1], pos: [0, 0.3], ori: 0.0, units: psychoJS.window.units,
    labels: [0, 1, 2, 3, 4, 5, 6], fontSize: 0.05, ticks: [],
    granularity: 1, style: ["RADIO"],
    color: new util.Color('LightGray'), markerColor: new util.Color('Red'), lineColor: new util.Color('White'), 
    opacity: undefined, fontFamily: 'Open Sans', bold: true, italic: false, depth: -1, 
    flip: false,
  });
  
  slider_6 = new visual.Slider({
    win: psychoJS.window, name: 'slider_6',
    startValue: undefined,
    size: [1.0, 0.1], pos: [0, 0], ori: 0.0, units: psychoJS.window.units,
    labels: [7, 8, 9, 10, 11, 12, 13], fontSize: 0.05, ticks: [],
    granularity: 1, style: ["RADIO"],
    color: new util.Color('LightGray'), markerColor: new util.Color('Red'), lineColor: new util.Color('White'), 
    opacity: undefined, fontFamily: 'Open Sans', bold: true, italic: false, depth: -2, 
    flip: false,
  });
  
  slider_7 = new visual.Slider({
    win: psychoJS.window, name: 'slider_7',
    startValue: undefined,
    size: [1.0, 0.1], pos: [0, (- 0.3)], ori: 0.0, units: psychoJS.window.units,
    labels: [14, 15, 16, 17, 18, 19, 20], fontSize: 0.05, ticks: [],
    granularity: 1, style: ["RADIO"],
    color: new util.Color('LightGray'), markerColor: new util.Color('Red'), lineColor: new util.Color('White'), 
    opacity: undefined, fontFamily: 'Open Sans', bold: true, italic: false, depth: -3, 
    flip: false,
  });
  
  // Initialize components for Routine "ast_welcome"
  ast_welcomeClock = new util.Clock();
  text_7 = new visual.TextStim({
    win: psychoJS.window,
    name: 'text_7',
    text: 'In Experiment 4, \n\nWe will play some ambient scene sounds. No response is required from you. \n\nWhen you are ready, click the left mouse button to start',
    font: 'Open Sans',
    units: undefined, 
    pos: [0, 0], draggable: false, height: 0.05,  wrapWidth: undefined, ori: 0.0,
    languageStyle: 'LTR',
    color: new util.Color('white'),  opacity: undefined,
    depth: 0.0 
  });
  
  mouse_4 = new core.Mouse({
    win: psychoJS.window,
  });
  mouse_4.mouseClock = new util.Clock();
  // Initialize components for Routine "ast_prestim"
  ast_prestimClock = new util.Clock();
  black_screen_9 = new visual.Rect ({
    win: psychoJS.window, name: 'black_screen_9', 
    width: [2, 1][0], height: [2, 1][1],
    ori: 0.0, 
    pos: [0, 0], 
    draggable: false, 
    anchor: 'center', 
    lineWidth: 1.0, 
    lineColor: new util.Color([(- 1.0), (- 1.0), (- 1.0)]), 
    fillColor: new util.Color([(- 1.0), (- 1.0), (- 1.0)]), 
    colorSpace: 'rgb', 
    opacity: undefined, 
    depth: -1, 
    interpolate: true, 
  });
  
  cross_13 = new visual.ShapeStim ({
    win: psychoJS.window, name: 'cross_13', 
    vertices: 'cross', size:[0.3, 0.3],
    ori: 0.0, 
    pos: [0, 0], 
    draggable: false, 
    anchor: 'center', 
    lineWidth: 1.0, 
    lineColor: new util.Color('white'), 
    fillColor: new util.Color('white'), 
    colorSpace: 'rgb', 
    opacity: undefined, 
    depth: -2, 
    interpolate: true, 
  });
  
  // Initialize components for Routine "stim"
  stimClock = new util.Clock();
  current_sound = new sound.Sound({
      win: psychoJS.window,
      value: 'A',
      secs: (- 1),
      });
  current_sound.setVolume(1.0);
  cross_14 = new visual.ShapeStim ({
    win: psychoJS.window, name: 'cross_14', 
    vertices: 'cross', size:[0.3, 0.3],
    ori: 0.0, 
    pos: [0, 0], 
    draggable: false, 
    anchor: 'center', 
    lineWidth: 1.0, 
    lineColor: new util.Color('white'), 
    fillColor: new util.Color('white'), 
    colorSpace: 'rgb', 
    opacity: undefined, 
    depth: -2, 
    interpolate: true, 
  });
  
  // Initialize components for Routine "post_stim"
  post_stimClock = new util.Clock();
  black_screen_10 = new visual.Rect ({
    win: psychoJS.window, name: 'black_screen_10', 
    width: [2, 1][0], height: [2, 1][1],
    ori: 0.0, 
    pos: [0, 0], 
    draggable: false, 
    anchor: 'center', 
    lineWidth: 1.0, 
    lineColor: new util.Color([(- 1.0), (- 1.0), (- 1.0)]), 
    fillColor: new util.Color([(- 1.0), (- 1.0), (- 1.0)]), 
    colorSpace: 'rgb', 
    opacity: undefined, 
    depth: -1, 
    interpolate: true, 
  });
  
  cross_15 = new visual.ShapeStim ({
    win: psychoJS.window, name: 'cross_15', 
    vertices: 'cross', size:[0.3, 0.3],
    ori: 0.0, 
    pos: [0, 0], 
    draggable: false, 
    anchor: 'center', 
    lineWidth: 1.0, 
    lineColor: new util.Color('white'), 
    fillColor: new util.Color('white'), 
    colorSpace: 'rgb', 
    opacity: undefined, 
    depth: -2, 
    interpolate: true, 
  });
  
  // Initialize components for Routine "end_2"
  end_2Clock = new util.Clock();
  text_end = new visual.TextStim({
    win: psychoJS.window,
    name: 'text_end',
    text: 'The experiment has ended, thank you for participating!\n\nClick the left mouse button to exit and notify the research staff.',
    font: 'Open Sans',
    units: undefined, 
    pos: [0, 0], draggable: false, height: 0.05,  wrapWidth: undefined, ori: 0.0,
    languageStyle: 'LTR',
    color: new util.Color('white'),  opacity: undefined,
    depth: -1.0 
  });
  
  mouse_5 = new core.Mouse({
    win: psychoJS.window,
  });
  mouse_5.mouseClock = new util.Clock();
  // Create some handy timers
  globalClock = new util.Clock();  // to track the time since experiment started
  routineTimer = new util.CountdownTimer();  // to track time remaining of each (non-slip) routine
  
  return Scheduler.Event.NEXT;
}

function welcomeRoutineBegin(snapshot) {
  return async function () {
    TrialHandler.fromSnapshot(snapshot); // ensure that .thisN vals are up to date
    
    //--- Prepare to start Routine 'welcome' ---
    t = 0;
    frameN = -1;
    continueRoutine = true; // until we're told otherwise
    welcomeClock.reset();
    routineTimer.reset();
    welcomeMaxDurationReached = false;
    // update component parameters for each repeat
    // setup some python lists for storing info about the mouse
    // current position of the mouse:
    mouse.x = [];
    mouse.y = [];
    mouse.leftButton = [];
    mouse.midButton = [];
    mouse.rightButton = [];
    mouse.time = [];
    gotValidClick = false; // until a click is received
    welcomeMaxDuration = null
    // keep track of which components have finished
    welcomeComponents = [];
    welcomeComponents.push(text_2);
    welcomeComponents.push(mouse);
    
    for (const thisComponent of welcomeComponents)
      if ('status' in thisComponent)
        thisComponent.status = PsychoJS.Status.NOT_STARTED;
    return Scheduler.Event.NEXT;
  }
}

function welcomeRoutineEachFrame() {
  return async function () {
    //--- Loop for each frame of Routine 'welcome' ---
    // get current time
    t = welcomeClock.getTime();
    frameN = frameN + 1;// number of completed frames (so 0 is the first frame)
    // update/draw components on each frame
    
    // *text_2* updates
    if (t >= 0.0 && text_2.status === PsychoJS.Status.NOT_STARTED) {
      // keep track of start time/frame for later
      text_2.tStart = t;  // (not accounting for frame time here)
      text_2.frameNStart = frameN;  // exact frame index
      
      text_2.setAutoDraw(true);
    }
    
    // *mouse* updates
    if (t >= 0.0 && mouse.status === PsychoJS.Status.NOT_STARTED) {
      // keep track of start time/frame for later
      mouse.tStart = t;  // (not accounting for frame time here)
      mouse.frameNStart = frameN;  // exact frame index
      
      mouse.status = PsychoJS.Status.STARTED;
      mouse.mouseClock.reset();
      prevButtonState = mouse.getPressed();  // if button is down already this ISN'T a new click
      }
    if (mouse.status === PsychoJS.Status.STARTED) {  // only update if started and not finished!
      _mouseButtons = mouse.getPressed();
      if (!_mouseButtons.every( (e,i,) => (e == prevButtonState[i]) )) { // button state changed?
        prevButtonState = _mouseButtons;
        if (_mouseButtons.reduce( (e, acc) => (e+acc) ) > 0) { // state changed to a new click
          _mouseXYs = mouse.getPos();
          mouse.x.push(_mouseXYs[0]);
          mouse.y.push(_mouseXYs[1]);
          mouse.leftButton.push(_mouseButtons[0]);
          mouse.midButton.push(_mouseButtons[1]);
          mouse.rightButton.push(_mouseButtons[2]);
          mouse.time.push(mouse.mouseClock.getTime());
          // end routine on response
          continueRoutine = false;
        }
      }
    }
    // check for quit (typically the Esc key)
    if (psychoJS.experiment.experimentEnded || psychoJS.eventManager.getKeys({keyList:['escape']}).length > 0) {
      return quitPsychoJS('The [Escape] key was pressed. Goodbye!', false);
    }
    
    // check if the Routine should terminate
    if (!continueRoutine) {  // a component has requested a forced-end of Routine
      return Scheduler.Event.NEXT;
    }
    
    continueRoutine = false;  // reverts to True if at least one component still running
    for (const thisComponent of welcomeComponents)
      if ('status' in thisComponent && thisComponent.status !== PsychoJS.Status.FINISHED) {
        continueRoutine = true;
        break;
      }
    
    // refresh the screen if continuing
    if (continueRoutine) {
      return Scheduler.Event.FLIP_REPEAT;
    } else {
      return Scheduler.Event.NEXT;
    }
  };
}

function welcomeRoutineEnd(snapshot) {
  return async function () {
    //--- Ending Routine 'welcome' ---
    for (const thisComponent of welcomeComponents) {
      if (typeof thisComponent.setAutoDraw === 'function') {
        thisComponent.setAutoDraw(false);
      }
    }
    // store data for psychoJS.experiment (ExperimentHandler)
    psychoJS.experiment.addData('mouse.x', mouse.x);
    psychoJS.experiment.addData('mouse.y', mouse.y);
    psychoJS.experiment.addData('mouse.leftButton', mouse.leftButton);
    psychoJS.experiment.addData('mouse.midButton', mouse.midButton);
    psychoJS.experiment.addData('mouse.rightButton', mouse.rightButton);
    psychoJS.experiment.addData('mouse.time', mouse.time);
    
    // the Routine "welcome" was not non-slip safe, so reset the non-slip timer
    routineTimer.reset();
    
    // Routines running outside a loop should always advance the datafile row
    if (currentLoop === psychoJS.experiment) {
      psychoJS.experiment.nextEntry(snapshot);
    }
    return Scheduler.Event.NEXT;
  }
}

function trials_pmtLoopBegin(trials_pmtLoopScheduler, snapshot) {
  return async function() {
    TrialHandler.fromSnapshot(snapshot); // update internal variables (.thisN etc) of the loop
    
    // set up handler to look after randomisation of conditions etc
    trials_pmt = new TrialHandler({
      psychoJS: psychoJS,
      nReps: pmt_trials, method: TrialHandler.Method.SEQUENTIAL,
      extraInfo: expInfo, originPath: undefined,
      trialList: undefined,
      seed: undefined, name: 'trials_pmt'
    });
    psychoJS.experiment.addLoop(trials_pmt); // add the loop to the experiment
    currentLoop = trials_pmt;  // we're now the current loop
    
    // Schedule all the trials in the trialList:
    for (const thisTrials_pmt of trials_pmt) {
      snapshot = trials_pmt.getSnapshot();
      trials_pmtLoopScheduler.add(importConditions(snapshot));
      trials_pmtLoopScheduler.add(pmt_prestimRoutineBegin(snapshot));
      trials_pmtLoopScheduler.add(pmt_prestimRoutineEachFrame());
      trials_pmtLoopScheduler.add(pmt_prestimRoutineEnd(snapshot));
      trials_pmtLoopScheduler.add(pmt_stimRoutineBegin(snapshot));
      trials_pmtLoopScheduler.add(pmt_stimRoutineEachFrame());
      trials_pmtLoopScheduler.add(pmt_stimRoutineEnd(snapshot));
      trials_pmtLoopScheduler.add(pmt_poststimRoutineBegin(snapshot));
      trials_pmtLoopScheduler.add(pmt_poststimRoutineEachFrame());
      trials_pmtLoopScheduler.add(pmt_poststimRoutineEnd(snapshot));
      trials_pmtLoopScheduler.add(trials_pmtLoopEndIteration(trials_pmtLoopScheduler, snapshot));
    }
    
    return Scheduler.Event.NEXT;
  }
}

async function trials_pmtLoopEnd() {
  // terminate loop
  psychoJS.experiment.removeLoop(trials_pmt);
  // update the current loop from the ExperimentHandler
  if (psychoJS.experiment._unfinishedLoops.length>0)
    currentLoop = psychoJS.experiment._unfinishedLoops.at(-1);
  else
    currentLoop = psychoJS.experiment;  // so we use addData from the experiment
  return Scheduler.Event.NEXT;
}

function trials_pmtLoopEndIteration(scheduler, snapshot) {
  // ------Prepare for next entry------
  return async function () {
    if (typeof snapshot !== 'undefined') {
      // ------Check if user ended loop early------
      if (snapshot.finished) {
        // Check for and save orphaned data
        if (psychoJS.experiment.isEntryEmpty()) {
          psychoJS.experiment.nextEntry(snapshot);
        }
        scheduler.stop();
      } else {
        psychoJS.experiment.nextEntry(snapshot);
      }
    return Scheduler.Event.NEXT;
    }
  };
}

function trials_hltLoopBegin(trials_hltLoopScheduler, snapshot) {
  return async function() {
    TrialHandler.fromSnapshot(snapshot); // update internal variables (.thisN etc) of the loop
    
    // set up handler to look after randomisation of conditions etc
    trials_hlt = new TrialHandler({
      psychoJS: psychoJS,
      nReps: hlt_trials, method: TrialHandler.Method.SEQUENTIAL,
      extraInfo: expInfo, originPath: undefined,
      trialList: undefined,
      seed: undefined, name: 'trials_hlt'
    });
    psychoJS.experiment.addLoop(trials_hlt); // add the loop to the experiment
    currentLoop = trials_hlt;  // we're now the current loop
    
    // Schedule all the trials in the trialList:
    for (const thisTrials_hlt of trials_hlt) {
      snapshot = trials_hlt.getSnapshot();
      trials_hltLoopScheduler.add(importConditions(snapshot));
      trials_hltLoopScheduler.add(hlt_prestimRoutineBegin(snapshot));
      trials_hltLoopScheduler.add(hlt_prestimRoutineEachFrame());
      trials_hltLoopScheduler.add(hlt_prestimRoutineEnd(snapshot));
      trials_hltLoopScheduler.add(hlt_stimRoutineBegin(snapshot));
      trials_hltLoopScheduler.add(hlt_stimRoutineEachFrame());
      trials_hltLoopScheduler.add(hlt_stimRoutineEnd(snapshot));
      trials_hltLoopScheduler.add(hlt_poststimRoutineBegin(snapshot));
      trials_hltLoopScheduler.add(hlt_poststimRoutineEachFrame());
      trials_hltLoopScheduler.add(hlt_poststimRoutineEnd(snapshot));
      trials_hltLoopScheduler.add(hlt_responseRoutineBegin(snapshot));
      trials_hltLoopScheduler.add(hlt_responseRoutineEachFrame());
      trials_hltLoopScheduler.add(hlt_responseRoutineEnd(snapshot));
      trials_hltLoopScheduler.add(trials_hltLoopEndIteration(trials_hltLoopScheduler, snapshot));
    }
    
    return Scheduler.Event.NEXT;
  }
}

async function trials_hltLoopEnd() {
  // terminate loop
  psychoJS.experiment.removeLoop(trials_hlt);
  // update the current loop from the ExperimentHandler
  if (psychoJS.experiment._unfinishedLoops.length>0)
    currentLoop = psychoJS.experiment._unfinishedLoops.at(-1);
  else
    currentLoop = psychoJS.experiment;  // so we use addData from the experiment
  return Scheduler.Event.NEXT;
}

function trials_hltLoopEndIteration(scheduler, snapshot) {
  // ------Prepare for next entry------
  return async function () {
    if (typeof snapshot !== 'undefined') {
      // ------Check if user ended loop early------
      if (snapshot.finished) {
        // Check for and save orphaned data
        if (psychoJS.experiment.isEntryEmpty()) {
          psychoJS.experiment.nextEntry(snapshot);
        }
        scheduler.stop();
      } else {
        psychoJS.experiment.nextEntry(snapshot);
      }
    return Scheduler.Event.NEXT;
    }
  };
}

function trials_letLoopBegin(trials_letLoopScheduler, snapshot) {
  return async function() {
    TrialHandler.fromSnapshot(snapshot); // update internal variables (.thisN etc) of the loop
    
    // set up handler to look after randomisation of conditions etc
    trials_let = new TrialHandler({
      psychoJS: psychoJS,
      nReps: let_trials, method: TrialHandler.Method.RANDOM,
      extraInfo: expInfo, originPath: undefined,
      trialList: undefined,
      seed: undefined, name: 'trials_let'
    });
    psychoJS.experiment.addLoop(trials_let); // add the loop to the experiment
    currentLoop = trials_let;  // we're now the current loop
    
    // Schedule all the trials in the trialList:
    for (const thisTrials_let of trials_let) {
      snapshot = trials_let.getSnapshot();
      trials_letLoopScheduler.add(importConditions(snapshot));
      trials_letLoopScheduler.add(let_prestimRoutineBegin(snapshot));
      trials_letLoopScheduler.add(let_prestimRoutineEachFrame());
      trials_letLoopScheduler.add(let_prestimRoutineEnd(snapshot));
      trials_letLoopScheduler.add(let_stimRoutineBegin(snapshot));
      trials_letLoopScheduler.add(let_stimRoutineEachFrame());
      trials_letLoopScheduler.add(let_stimRoutineEnd(snapshot));
      trials_letLoopScheduler.add(let_poststimRoutineBegin(snapshot));
      trials_letLoopScheduler.add(let_poststimRoutineEachFrame());
      trials_letLoopScheduler.add(let_poststimRoutineEnd(snapshot));
      trials_letLoopScheduler.add(let_responseRoutineBegin(snapshot));
      trials_letLoopScheduler.add(let_responseRoutineEachFrame());
      trials_letLoopScheduler.add(let_responseRoutineEnd(snapshot));
      trials_letLoopScheduler.add(trials_letLoopEndIteration(trials_letLoopScheduler, snapshot));
    }
    
    return Scheduler.Event.NEXT;
  }
}

async function trials_letLoopEnd() {
  // terminate loop
  psychoJS.experiment.removeLoop(trials_let);
  // update the current loop from the ExperimentHandler
  if (psychoJS.experiment._unfinishedLoops.length>0)
    currentLoop = psychoJS.experiment._unfinishedLoops.at(-1);
  else
    currentLoop = psychoJS.experiment;  // so we use addData from the experiment
  return Scheduler.Event.NEXT;
}

function trials_letLoopEndIteration(scheduler, snapshot) {
  // ------Prepare for next entry------
  return async function () {
    if (typeof snapshot !== 'undefined') {
      // ------Check if user ended loop early------
      if (snapshot.finished) {
        // Check for and save orphaned data
        if (psychoJS.experiment.isEntryEmpty()) {
          psychoJS.experiment.nextEntry(snapshot);
        }
        scheduler.stop();
      } else {
        psychoJS.experiment.nextEntry(snapshot);
      }
    return Scheduler.Event.NEXT;
    }
  };
}

function trials_astLoopBegin(trials_astLoopScheduler, snapshot) {
  return async function() {
    TrialHandler.fromSnapshot(snapshot); // update internal variables (.thisN etc) of the loop
    
    // set up handler to look after randomisation of conditions etc
    trials_ast = new TrialHandler({
      psychoJS: psychoJS,
      nReps: ast_trials, method: TrialHandler.Method.SEQUENTIAL,
      extraInfo: expInfo, originPath: undefined,
      trialList: undefined,
      seed: undefined, name: 'trials_ast'
    });
    psychoJS.experiment.addLoop(trials_ast); // add the loop to the experiment
    currentLoop = trials_ast;  // we're now the current loop
    
    // Schedule all the trials in the trialList:
    for (const thisTrials_ast of trials_ast) {
      snapshot = trials_ast.getSnapshot();
      trials_astLoopScheduler.add(importConditions(snapshot));
      trials_astLoopScheduler.add(ast_prestimRoutineBegin(snapshot));
      trials_astLoopScheduler.add(ast_prestimRoutineEachFrame());
      trials_astLoopScheduler.add(ast_prestimRoutineEnd(snapshot));
      trials_astLoopScheduler.add(stimRoutineBegin(snapshot));
      trials_astLoopScheduler.add(stimRoutineEachFrame());
      trials_astLoopScheduler.add(stimRoutineEnd(snapshot));
      trials_astLoopScheduler.add(post_stimRoutineBegin(snapshot));
      trials_astLoopScheduler.add(post_stimRoutineEachFrame());
      trials_astLoopScheduler.add(post_stimRoutineEnd(snapshot));
      trials_astLoopScheduler.add(trials_astLoopEndIteration(trials_astLoopScheduler, snapshot));
    }
    
    return Scheduler.Event.NEXT;
  }
}

async function trials_astLoopEnd() {
  // terminate loop
  psychoJS.experiment.removeLoop(trials_ast);
  // update the current loop from the ExperimentHandler
  if (psychoJS.experiment._unfinishedLoops.length>0)
    currentLoop = psychoJS.experiment._unfinishedLoops.at(-1);
  else
    currentLoop = psychoJS.experiment;  // so we use addData from the experiment
  return Scheduler.Event.NEXT;
}

function trials_astLoopEndIteration(scheduler, snapshot) {
  // ------Prepare for next entry------
  return async function () {
    if (typeof snapshot !== 'undefined') {
      // ------Check if user ended loop early------
      if (snapshot.finished) {
        // Check for and save orphaned data
        if (psychoJS.experiment.isEntryEmpty()) {
          psychoJS.experiment.nextEntry(snapshot);
        }
        scheduler.stop();
      } else {
        psychoJS.experiment.nextEntry(snapshot);
      }
    return Scheduler.Event.NEXT;
    }
  };
}

function pmt_prestimRoutineBegin(snapshot) {
  return async function () {
    TrialHandler.fromSnapshot(snapshot); // ensure that .thisN vals are up to date
    
    //--- Prepare to start Routine 'pmt_prestim' ---
    t = 0;
    frameN = -1;
    continueRoutine = true; // until we're told otherwise
    pmt_prestimClock.reset();
    routineTimer.reset();
    pmt_prestimMaxDurationReached = false;
    // update component parameters for each repeat
    psychoJS.experiment.addData('pmt_prestim.started', globalClock.getTime());
    pmt_prestimMaxDuration = null
    // keep track of which components have finished
    pmt_prestimComponents = [];
    pmt_prestimComponents.push(black_screen);
    pmt_prestimComponents.push(cross_7);
    
    for (const thisComponent of pmt_prestimComponents)
      if ('status' in thisComponent)
        thisComponent.status = PsychoJS.Status.NOT_STARTED;
    return Scheduler.Event.NEXT;
  }
}

function pmt_prestimRoutineEachFrame() {
  return async function () {
    //--- Loop for each frame of Routine 'pmt_prestim' ---
    // get current time
    t = pmt_prestimClock.getTime();
    frameN = frameN + 1;// number of completed frames (so 0 is the first frame)
    // update/draw components on each frame
    
    // *black_screen* updates
    if (t >= 0.0 && black_screen.status === PsychoJS.Status.NOT_STARTED) {
      // keep track of start time/frame for later
      black_screen.tStart = t;  // (not accounting for frame time here)
      black_screen.frameNStart = frameN;  // exact frame index
      
      black_screen.setAutoDraw(true);
    }
    
    frameRemains = 0.0 + pmt_prestim_duration - psychoJS.window.monitorFramePeriod * 0.75;// most of one frame period left
    if (black_screen.status === PsychoJS.Status.STARTED && t >= frameRemains) {
      black_screen.setAutoDraw(false);
    }
    
    
    // *cross_7* updates
    if (t >= 0.0 && cross_7.status === PsychoJS.Status.NOT_STARTED) {
      // keep track of start time/frame for later
      cross_7.tStart = t;  // (not accounting for frame time here)
      cross_7.frameNStart = frameN;  // exact frame index
      
      cross_7.setAutoDraw(true);
    }
    
    frameRemains = 0.0 + pmt_prestim_duration - psychoJS.window.monitorFramePeriod * 0.75;// most of one frame period left
    if (cross_7.status === PsychoJS.Status.STARTED && t >= frameRemains) {
      cross_7.setAutoDraw(false);
    }
    
    // check for quit (typically the Esc key)
    if (psychoJS.experiment.experimentEnded || psychoJS.eventManager.getKeys({keyList:['escape']}).length > 0) {
      return quitPsychoJS('The [Escape] key was pressed. Goodbye!', false);
    }
    
    // check if the Routine should terminate
    if (!continueRoutine) {  // a component has requested a forced-end of Routine
      return Scheduler.Event.NEXT;
    }
    
    continueRoutine = false;  // reverts to True if at least one component still running
    for (const thisComponent of pmt_prestimComponents)
      if ('status' in thisComponent && thisComponent.status !== PsychoJS.Status.FINISHED) {
        continueRoutine = true;
        break;
      }
    
    // refresh the screen if continuing
    if (continueRoutine) {
      return Scheduler.Event.FLIP_REPEAT;
    } else {
      return Scheduler.Event.NEXT;
    }
  };
}

function pmt_prestimRoutineEnd(snapshot) {
  return async function () {
    //--- Ending Routine 'pmt_prestim' ---
    for (const thisComponent of pmt_prestimComponents) {
      if (typeof thisComponent.setAutoDraw === 'function') {
        thisComponent.setAutoDraw(false);
      }
    }
    psychoJS.experiment.addData('pmt_prestim.stopped', globalClock.getTime());
    // the Routine "pmt_prestim" was not non-slip safe, so reset the non-slip timer
    routineTimer.reset();
    
    // Routines running outside a loop should always advance the datafile row
    if (currentLoop === psychoJS.experiment) {
      psychoJS.experiment.nextEntry(snapshot);
    }
    return Scheduler.Event.NEXT;
  }
}

function pmt_stimRoutineBegin(snapshot) {
  return async function () {
    TrialHandler.fromSnapshot(snapshot); // ensure that .thisN vals are up to date
    
    //--- Prepare to start Routine 'pmt_stim' ---
    t = 0;
    frameN = -1;
    continueRoutine = true; // until we're told otherwise
    pmt_stimClock.reset();
    routineTimer.reset();
    pmt_stimMaxDurationReached = false;
    // update component parameters for each repeat
    psychoJS.experiment.addData('pmt_stim.started', globalClock.getTime());
    pmt_stimMaxDuration = null
    // keep track of which components have finished
    pmt_stimComponents = [];
    pmt_stimComponents.push(gray_screen);
    pmt_stimComponents.push(cross_8);
    
    for (const thisComponent of pmt_stimComponents)
      if ('status' in thisComponent)
        thisComponent.status = PsychoJS.Status.NOT_STARTED;
    return Scheduler.Event.NEXT;
  }
}

function pmt_stimRoutineEachFrame() {
  return async function () {
    //--- Loop for each frame of Routine 'pmt_stim' ---
    // get current time
    t = pmt_stimClock.getTime();
    frameN = frameN + 1;// number of completed frames (so 0 is the first frame)
    // update/draw components on each frame
    
    // *gray_screen* updates
    if (t >= 0 && gray_screen.status === PsychoJS.Status.NOT_STARTED) {
      // keep track of start time/frame for later
      gray_screen.tStart = t;  // (not accounting for frame time here)
      gray_screen.frameNStart = frameN;  // exact frame index
      
      gray_screen.setAutoDraw(true);
    }
    
    frameRemains = 0 + pmt_stim_duration - psychoJS.window.monitorFramePeriod * 0.75;// most of one frame period left
    if (gray_screen.status === PsychoJS.Status.STARTED && t >= frameRemains) {
      gray_screen.setAutoDraw(false);
    }
    
    
    // *cross_8* updates
    if (t >= 0.0 && cross_8.status === PsychoJS.Status.NOT_STARTED) {
      // keep track of start time/frame for later
      cross_8.tStart = t;  // (not accounting for frame time here)
      cross_8.frameNStart = frameN;  // exact frame index
      
      cross_8.setAutoDraw(true);
    }
    
    frameRemains = 0.0 + pmt_stim_duration - psychoJS.window.monitorFramePeriod * 0.75;// most of one frame period left
    if (cross_8.status === PsychoJS.Status.STARTED && t >= frameRemains) {
      cross_8.setAutoDraw(false);
    }
    
    // check for quit (typically the Esc key)
    if (psychoJS.experiment.experimentEnded || psychoJS.eventManager.getKeys({keyList:['escape']}).length > 0) {
      return quitPsychoJS('The [Escape] key was pressed. Goodbye!', false);
    }
    
    // check if the Routine should terminate
    if (!continueRoutine) {  // a component has requested a forced-end of Routine
      return Scheduler.Event.NEXT;
    }
    
    continueRoutine = false;  // reverts to True if at least one component still running
    for (const thisComponent of pmt_stimComponents)
      if ('status' in thisComponent && thisComponent.status !== PsychoJS.Status.FINISHED) {
        continueRoutine = true;
        break;
      }
    
    // refresh the screen if continuing
    if (continueRoutine) {
      return Scheduler.Event.FLIP_REPEAT;
    } else {
      return Scheduler.Event.NEXT;
    }
  };
}

function pmt_stimRoutineEnd(snapshot) {
  return async function () {
    //--- Ending Routine 'pmt_stim' ---
    for (const thisComponent of pmt_stimComponents) {
      if (typeof thisComponent.setAutoDraw === 'function') {
        thisComponent.setAutoDraw(false);
      }
    }
    psychoJS.experiment.addData('pmt_stim.stopped', globalClock.getTime());
    // the Routine "pmt_stim" was not non-slip safe, so reset the non-slip timer
    routineTimer.reset();
    
    // Routines running outside a loop should always advance the datafile row
    if (currentLoop === psychoJS.experiment) {
      psychoJS.experiment.nextEntry(snapshot);
    }
    return Scheduler.Event.NEXT;
  }
}

function pmt_poststimRoutineBegin(snapshot) {
  return async function () {
    TrialHandler.fromSnapshot(snapshot); // ensure that .thisN vals are up to date
    
    //--- Prepare to start Routine 'pmt_poststim' ---
    t = 0;
    frameN = -1;
    continueRoutine = true; // until we're told otherwise
    pmt_poststimClock.reset();
    routineTimer.reset();
    pmt_poststimMaxDurationReached = false;
    // update component parameters for each repeat
    psychoJS.experiment.addData('pmt_poststim.started', globalClock.getTime());
    pmt_poststimMaxDuration = null
    // keep track of which components have finished
    pmt_poststimComponents = [];
    pmt_poststimComponents.push(black_screen_2);
    pmt_poststimComponents.push(cross_9);
    
    for (const thisComponent of pmt_poststimComponents)
      if ('status' in thisComponent)
        thisComponent.status = PsychoJS.Status.NOT_STARTED;
    return Scheduler.Event.NEXT;
  }
}

function pmt_poststimRoutineEachFrame() {
  return async function () {
    //--- Loop for each frame of Routine 'pmt_poststim' ---
    // get current time
    t = pmt_poststimClock.getTime();
    frameN = frameN + 1;// number of completed frames (so 0 is the first frame)
    // update/draw components on each frame
    
    // *black_screen_2* updates
    if (t >= 0.0 && black_screen_2.status === PsychoJS.Status.NOT_STARTED) {
      // keep track of start time/frame for later
      black_screen_2.tStart = t;  // (not accounting for frame time here)
      black_screen_2.frameNStart = frameN;  // exact frame index
      
      black_screen_2.setAutoDraw(true);
    }
    
    frameRemains = 0.0 + pmt_poststim_duration - psychoJS.window.monitorFramePeriod * 0.75;// most of one frame period left
    if (black_screen_2.status === PsychoJS.Status.STARTED && t >= frameRemains) {
      black_screen_2.setAutoDraw(false);
    }
    
    
    // *cross_9* updates
    if (t >= 0.0 && cross_9.status === PsychoJS.Status.NOT_STARTED) {
      // keep track of start time/frame for later
      cross_9.tStart = t;  // (not accounting for frame time here)
      cross_9.frameNStart = frameN;  // exact frame index
      
      cross_9.setAutoDraw(true);
    }
    
    frameRemains = 0.0 + pmt_poststim_duration - psychoJS.window.monitorFramePeriod * 0.75;// most of one frame period left
    if (cross_9.status === PsychoJS.Status.STARTED && t >= frameRemains) {
      cross_9.setAutoDraw(false);
    }
    
    // check for quit (typically the Esc key)
    if (psychoJS.experiment.experimentEnded || psychoJS.eventManager.getKeys({keyList:['escape']}).length > 0) {
      return quitPsychoJS('The [Escape] key was pressed. Goodbye!', false);
    }
    
    // check if the Routine should terminate
    if (!continueRoutine) {  // a component has requested a forced-end of Routine
      return Scheduler.Event.NEXT;
    }
    
    continueRoutine = false;  // reverts to True if at least one component still running
    for (const thisComponent of pmt_poststimComponents)
      if ('status' in thisComponent && thisComponent.status !== PsychoJS.Status.FINISHED) {
        continueRoutine = true;
        break;
      }
    
    // refresh the screen if continuing
    if (continueRoutine) {
      return Scheduler.Event.FLIP_REPEAT;
    } else {
      return Scheduler.Event.NEXT;
    }
  };
}

function pmt_poststimRoutineEnd(snapshot) {
  return async function () {
    //--- Ending Routine 'pmt_poststim' ---
    for (const thisComponent of pmt_poststimComponents) {
      if (typeof thisComponent.setAutoDraw === 'function') {
        thisComponent.setAutoDraw(false);
      }
    }
    psychoJS.experiment.addData('pmt_poststim.stopped', globalClock.getTime());
    // the Routine "pmt_poststim" was not non-slip safe, so reset the non-slip timer
    routineTimer.reset();
    
    // Routines running outside a loop should always advance the datafile row
    if (currentLoop === psychoJS.experiment) {
      psychoJS.experiment.nextEntry(snapshot);
    }
    return Scheduler.Event.NEXT;
  }
}

function hlt_welcomeRoutineBegin(snapshot) {
  return async function () {
    TrialHandler.fromSnapshot(snapshot); // ensure that .thisN vals are up to date
    
    //--- Prepare to start Routine 'hlt_welcome' ---
    t = 0;
    frameN = -1;
    continueRoutine = true; // until we're told otherwise
    hlt_welcomeClock.reset();
    routineTimer.reset();
    hlt_welcomeMaxDurationReached = false;
    // update component parameters for each repeat
    // setup some python lists for storing info about the mouse_2
    // current position of the mouse:
    mouse_2.x = [];
    mouse_2.y = [];
    mouse_2.leftButton = [];
    mouse_2.midButton = [];
    mouse_2.rightButton = [];
    mouse_2.time = [];
    gotValidClick = false; // until a click is received
    psychoJS.experiment.addData('hlt_welcome.started', globalClock.getTime());
    hlt_welcomeMaxDuration = null
    // keep track of which components have finished
    hlt_welcomeComponents = [];
    hlt_welcomeComponents.push(text);
    hlt_welcomeComponents.push(mouse_2);
    
    for (const thisComponent of hlt_welcomeComponents)
      if ('status' in thisComponent)
        thisComponent.status = PsychoJS.Status.NOT_STARTED;
    return Scheduler.Event.NEXT;
  }
}

function hlt_welcomeRoutineEachFrame() {
  return async function () {
    //--- Loop for each frame of Routine 'hlt_welcome' ---
    // get current time
    t = hlt_welcomeClock.getTime();
    frameN = frameN + 1;// number of completed frames (so 0 is the first frame)
    // update/draw components on each frame
    
    // *text* updates
    if (t >= 0.0 && text.status === PsychoJS.Status.NOT_STARTED) {
      // keep track of start time/frame for later
      text.tStart = t;  // (not accounting for frame time here)
      text.frameNStart = frameN;  // exact frame index
      
      text.setAutoDraw(true);
    }
    
    // *mouse_2* updates
    if (t >= 0.0 && mouse_2.status === PsychoJS.Status.NOT_STARTED) {
      // keep track of start time/frame for later
      mouse_2.tStart = t;  // (not accounting for frame time here)
      mouse_2.frameNStart = frameN;  // exact frame index
      
      mouse_2.status = PsychoJS.Status.STARTED;
      mouse_2.mouseClock.reset();
      prevButtonState = mouse_2.getPressed();  // if button is down already this ISN'T a new click
      }
    if (mouse_2.status === PsychoJS.Status.STARTED) {  // only update if started and not finished!
      _mouseButtons = mouse_2.getPressed();
      if (!_mouseButtons.every( (e,i,) => (e == prevButtonState[i]) )) { // button state changed?
        prevButtonState = _mouseButtons;
        if (_mouseButtons.reduce( (e, acc) => (e+acc) ) > 0) { // state changed to a new click
          _mouseXYs = mouse_2.getPos();
          mouse_2.x.push(_mouseXYs[0]);
          mouse_2.y.push(_mouseXYs[1]);
          mouse_2.leftButton.push(_mouseButtons[0]);
          mouse_2.midButton.push(_mouseButtons[1]);
          mouse_2.rightButton.push(_mouseButtons[2]);
          mouse_2.time.push(mouse_2.mouseClock.getTime());
          // end routine on response
          continueRoutine = false;
        }
      }
    }
    // check for quit (typically the Esc key)
    if (psychoJS.experiment.experimentEnded || psychoJS.eventManager.getKeys({keyList:['escape']}).length > 0) {
      return quitPsychoJS('The [Escape] key was pressed. Goodbye!', false);
    }
    
    // check if the Routine should terminate
    if (!continueRoutine) {  // a component has requested a forced-end of Routine
      return Scheduler.Event.NEXT;
    }
    
    continueRoutine = false;  // reverts to True if at least one component still running
    for (const thisComponent of hlt_welcomeComponents)
      if ('status' in thisComponent && thisComponent.status !== PsychoJS.Status.FINISHED) {
        continueRoutine = true;
        break;
      }
    
    // refresh the screen if continuing
    if (continueRoutine) {
      return Scheduler.Event.FLIP_REPEAT;
    } else {
      return Scheduler.Event.NEXT;
    }
  };
}

function hlt_welcomeRoutineEnd(snapshot) {
  return async function () {
    //--- Ending Routine 'hlt_welcome' ---
    for (const thisComponent of hlt_welcomeComponents) {
      if (typeof thisComponent.setAutoDraw === 'function') {
        thisComponent.setAutoDraw(false);
      }
    }
    psychoJS.experiment.addData('hlt_welcome.stopped', globalClock.getTime());
    // store data for psychoJS.experiment (ExperimentHandler)
    psychoJS.experiment.addData('mouse_2.x', mouse_2.x);
    psychoJS.experiment.addData('mouse_2.y', mouse_2.y);
    psychoJS.experiment.addData('mouse_2.leftButton', mouse_2.leftButton);
    psychoJS.experiment.addData('mouse_2.midButton', mouse_2.midButton);
    psychoJS.experiment.addData('mouse_2.rightButton', mouse_2.rightButton);
    psychoJS.experiment.addData('mouse_2.time', mouse_2.time);
    
    // the Routine "hlt_welcome" was not non-slip safe, so reset the non-slip timer
    routineTimer.reset();
    
    // Routines running outside a loop should always advance the datafile row
    if (currentLoop === psychoJS.experiment) {
      psychoJS.experiment.nextEntry(snapshot);
    }
    return Scheduler.Event.NEXT;
  }
}

function hlt_prestimRoutineBegin(snapshot) {
  return async function () {
    TrialHandler.fromSnapshot(snapshot); // ensure that .thisN vals are up to date
    
    //--- Prepare to start Routine 'hlt_prestim' ---
    t = 0;
    frameN = -1;
    continueRoutine = true; // until we're told otherwise
    hlt_prestimClock.reset();
    routineTimer.reset();
    hlt_prestimMaxDurationReached = false;
    // update component parameters for each repeat
    psychoJS.experiment.addData('hlt_prestim.started', globalClock.getTime());
    hlt_prestimMaxDuration = null
    // keep track of which components have finished
    hlt_prestimComponents = [];
    hlt_prestimComponents.push(black_screen_3);
    hlt_prestimComponents.push(cross_2);
    
    for (const thisComponent of hlt_prestimComponents)
      if ('status' in thisComponent)
        thisComponent.status = PsychoJS.Status.NOT_STARTED;
    return Scheduler.Event.NEXT;
  }
}

function hlt_prestimRoutineEachFrame() {
  return async function () {
    //--- Loop for each frame of Routine 'hlt_prestim' ---
    // get current time
    t = hlt_prestimClock.getTime();
    frameN = frameN + 1;// number of completed frames (so 0 is the first frame)
    // update/draw components on each frame
    
    // *black_screen_3* updates
    if (t >= 0.0 && black_screen_3.status === PsychoJS.Status.NOT_STARTED) {
      // keep track of start time/frame for later
      black_screen_3.tStart = t;  // (not accounting for frame time here)
      black_screen_3.frameNStart = frameN;  // exact frame index
      
      black_screen_3.setAutoDraw(true);
    }
    
    frameRemains = 0.0 + hlt_prestim_duration - psychoJS.window.monitorFramePeriod * 0.75;// most of one frame period left
    if (black_screen_3.status === PsychoJS.Status.STARTED && t >= frameRemains) {
      black_screen_3.setAutoDraw(false);
    }
    
    
    // *cross_2* updates
    if (t >= 0.0 && cross_2.status === PsychoJS.Status.NOT_STARTED) {
      // keep track of start time/frame for later
      cross_2.tStart = t;  // (not accounting for frame time here)
      cross_2.frameNStart = frameN;  // exact frame index
      
      cross_2.setAutoDraw(true);
    }
    
    frameRemains = 0.0 + hlt_prestim_duration - psychoJS.window.monitorFramePeriod * 0.75;// most of one frame period left
    if (cross_2.status === PsychoJS.Status.STARTED && t >= frameRemains) {
      cross_2.setAutoDraw(false);
    }
    
    // check for quit (typically the Esc key)
    if (psychoJS.experiment.experimentEnded || psychoJS.eventManager.getKeys({keyList:['escape']}).length > 0) {
      return quitPsychoJS('The [Escape] key was pressed. Goodbye!', false);
    }
    
    // check if the Routine should terminate
    if (!continueRoutine) {  // a component has requested a forced-end of Routine
      return Scheduler.Event.NEXT;
    }
    
    continueRoutine = false;  // reverts to True if at least one component still running
    for (const thisComponent of hlt_prestimComponents)
      if ('status' in thisComponent && thisComponent.status !== PsychoJS.Status.FINISHED) {
        continueRoutine = true;
        break;
      }
    
    // refresh the screen if continuing
    if (continueRoutine) {
      return Scheduler.Event.FLIP_REPEAT;
    } else {
      return Scheduler.Event.NEXT;
    }
  };
}

function hlt_prestimRoutineEnd(snapshot) {
  return async function () {
    //--- Ending Routine 'hlt_prestim' ---
    for (const thisComponent of hlt_prestimComponents) {
      if (typeof thisComponent.setAutoDraw === 'function') {
        thisComponent.setAutoDraw(false);
      }
    }
    psychoJS.experiment.addData('hlt_prestim.stopped', globalClock.getTime());
    // the Routine "hlt_prestim" was not non-slip safe, so reset the non-slip timer
    routineTimer.reset();
    
    // Routines running outside a loop should always advance the datafile row
    if (currentLoop === psychoJS.experiment) {
      psychoJS.experiment.nextEntry(snapshot);
    }
    return Scheduler.Event.NEXT;
  }
}

function hlt_stimRoutineBegin(snapshot) {
  return async function () {
    TrialHandler.fromSnapshot(snapshot); // ensure that .thisN vals are up to date
    
    //--- Prepare to start Routine 'hlt_stim' ---
    t = 0;
    frameN = -1;
    continueRoutine = true; // until we're told otherwise
    hlt_stimClock.reset();
    routineTimer.reset();
    hlt_stimMaxDurationReached = false;
    // update component parameters for each repeat
    hlt_sound.setValue(sound_path);
    hlt_sound.secs=hlt_stim_duration;
    hlt_sound.setVolume(1.0);
    psychoJS.experiment.addData('hlt_stim.started', globalClock.getTime());
    hlt_stimMaxDuration = null
    // keep track of which components have finished
    hlt_stimComponents = [];
    hlt_stimComponents.push(hlt_sound);
    hlt_stimComponents.push(black_screen_4);
    hlt_stimComponents.push(cross_5);
    
    for (const thisComponent of hlt_stimComponents)
      if ('status' in thisComponent)
        thisComponent.status = PsychoJS.Status.NOT_STARTED;
    return Scheduler.Event.NEXT;
  }
}

function hlt_stimRoutineEachFrame() {
  return async function () {
    //--- Loop for each frame of Routine 'hlt_stim' ---
    // get current time
    t = hlt_stimClock.getTime();
    frameN = frameN + 1;// number of completed frames (so 0 is the first frame)
    // update/draw components on each frame
    // start/stop hlt_sound
    if (t >= 0.0 && hlt_sound.status === PsychoJS.Status.NOT_STARTED) {
      // keep track of start time/frame for later
      hlt_sound.tStart = t;  // (not accounting for frame time here)
      hlt_sound.frameNStart = frameN;  // exact frame index
      
      psychoJS.window.callOnFlip(function(){ hlt_sound.play(); });  // screen flip
      hlt_sound.status = PsychoJS.Status.STARTED;
    }
    frameRemains = 0.0 + hlt_stim_duration - psychoJS.window.monitorFramePeriod * 0.75;// most of one frame period left
    if (hlt_sound.status === PsychoJS.Status.STARTED && t >= frameRemains) {
      if (t >= hlt_sound.tStart + 0.5) {
        hlt_sound.stop();  // stop the sound (if longer than duration)
        hlt_sound.status = PsychoJS.Status.FINISHED;
      }
    }
    
    // *black_screen_4* updates
    if (t >= 0.0 && black_screen_4.status === PsychoJS.Status.NOT_STARTED) {
      // keep track of start time/frame for later
      black_screen_4.tStart = t;  // (not accounting for frame time here)
      black_screen_4.frameNStart = frameN;  // exact frame index
      
      black_screen_4.setAutoDraw(true);
    }
    
    frameRemains = 0.0 + hlt_stim_duration - psychoJS.window.monitorFramePeriod * 0.75;// most of one frame period left
    if (black_screen_4.status === PsychoJS.Status.STARTED && t >= frameRemains) {
      black_screen_4.setAutoDraw(false);
    }
    
    
    // *cross_5* updates
    if (t >= 0.0 && cross_5.status === PsychoJS.Status.NOT_STARTED) {
      // keep track of start time/frame for later
      cross_5.tStart = t;  // (not accounting for frame time here)
      cross_5.frameNStart = frameN;  // exact frame index
      
      cross_5.setAutoDraw(true);
    }
    
    frameRemains = 0.0 + hlt_stim_duration - psychoJS.window.monitorFramePeriod * 0.75;// most of one frame period left
    if (cross_5.status === PsychoJS.Status.STARTED && t >= frameRemains) {
      cross_5.setAutoDraw(false);
    }
    
    // check for quit (typically the Esc key)
    if (psychoJS.experiment.experimentEnded || psychoJS.eventManager.getKeys({keyList:['escape']}).length > 0) {
      return quitPsychoJS('The [Escape] key was pressed. Goodbye!', false);
    }
    
    // check if the Routine should terminate
    if (!continueRoutine) {  // a component has requested a forced-end of Routine
      return Scheduler.Event.NEXT;
    }
    
    continueRoutine = false;  // reverts to True if at least one component still running
    for (const thisComponent of hlt_stimComponents)
      if ('status' in thisComponent && thisComponent.status !== PsychoJS.Status.FINISHED) {
        continueRoutine = true;
        break;
      }
    
    // refresh the screen if continuing
    if (continueRoutine) {
      return Scheduler.Event.FLIP_REPEAT;
    } else {
      return Scheduler.Event.NEXT;
    }
  };
}

function hlt_stimRoutineEnd(snapshot) {
  return async function () {
    //--- Ending Routine 'hlt_stim' ---
    for (const thisComponent of hlt_stimComponents) {
      if (typeof thisComponent.setAutoDraw === 'function') {
        thisComponent.setAutoDraw(false);
      }
    }
    psychoJS.experiment.addData('hlt_stim.stopped', globalClock.getTime());
    hlt_sound.stop();  // ensure sound has stopped at end of Routine
    // the Routine "hlt_stim" was not non-slip safe, so reset the non-slip timer
    routineTimer.reset();
    
    // Routines running outside a loop should always advance the datafile row
    if (currentLoop === psychoJS.experiment) {
      psychoJS.experiment.nextEntry(snapshot);
    }
    return Scheduler.Event.NEXT;
  }
}

function hlt_poststimRoutineBegin(snapshot) {
  return async function () {
    TrialHandler.fromSnapshot(snapshot); // ensure that .thisN vals are up to date
    
    //--- Prepare to start Routine 'hlt_poststim' ---
    t = 0;
    frameN = -1;
    continueRoutine = true; // until we're told otherwise
    hlt_poststimClock.reset();
    routineTimer.reset();
    hlt_poststimMaxDurationReached = false;
    // update component parameters for each repeat
    psychoJS.experiment.addData('hlt_poststim.started', globalClock.getTime());
    hlt_poststimMaxDuration = null
    // keep track of which components have finished
    hlt_poststimComponents = [];
    hlt_poststimComponents.push(black_screen_5);
    hlt_poststimComponents.push(cross_6);
    
    for (const thisComponent of hlt_poststimComponents)
      if ('status' in thisComponent)
        thisComponent.status = PsychoJS.Status.NOT_STARTED;
    return Scheduler.Event.NEXT;
  }
}

function hlt_poststimRoutineEachFrame() {
  return async function () {
    //--- Loop for each frame of Routine 'hlt_poststim' ---
    // get current time
    t = hlt_poststimClock.getTime();
    frameN = frameN + 1;// number of completed frames (so 0 is the first frame)
    // update/draw components on each frame
    
    // *black_screen_5* updates
    if (t >= 0.0 && black_screen_5.status === PsychoJS.Status.NOT_STARTED) {
      // keep track of start time/frame for later
      black_screen_5.tStart = t;  // (not accounting for frame time here)
      black_screen_5.frameNStart = frameN;  // exact frame index
      
      black_screen_5.setAutoDraw(true);
    }
    
    frameRemains = 0.0 + hlt_poststim_duration - psychoJS.window.monitorFramePeriod * 0.75;// most of one frame period left
    if (black_screen_5.status === PsychoJS.Status.STARTED && t >= frameRemains) {
      black_screen_5.setAutoDraw(false);
    }
    
    
    // *cross_6* updates
    if (t >= 0.0 && cross_6.status === PsychoJS.Status.NOT_STARTED) {
      // keep track of start time/frame for later
      cross_6.tStart = t;  // (not accounting for frame time here)
      cross_6.frameNStart = frameN;  // exact frame index
      
      cross_6.setAutoDraw(true);
    }
    
    frameRemains = 0.0 + hlt_poststim_duration - psychoJS.window.monitorFramePeriod * 0.75;// most of one frame period left
    if (cross_6.status === PsychoJS.Status.STARTED && t >= frameRemains) {
      cross_6.setAutoDraw(false);
    }
    
    // check for quit (typically the Esc key)
    if (psychoJS.experiment.experimentEnded || psychoJS.eventManager.getKeys({keyList:['escape']}).length > 0) {
      return quitPsychoJS('The [Escape] key was pressed. Goodbye!', false);
    }
    
    // check if the Routine should terminate
    if (!continueRoutine) {  // a component has requested a forced-end of Routine
      return Scheduler.Event.NEXT;
    }
    
    continueRoutine = false;  // reverts to True if at least one component still running
    for (const thisComponent of hlt_poststimComponents)
      if ('status' in thisComponent && thisComponent.status !== PsychoJS.Status.FINISHED) {
        continueRoutine = true;
        break;
      }
    
    // refresh the screen if continuing
    if (continueRoutine) {
      return Scheduler.Event.FLIP_REPEAT;
    } else {
      return Scheduler.Event.NEXT;
    }
  };
}

function hlt_poststimRoutineEnd(snapshot) {
  return async function () {
    //--- Ending Routine 'hlt_poststim' ---
    for (const thisComponent of hlt_poststimComponents) {
      if (typeof thisComponent.setAutoDraw === 'function') {
        thisComponent.setAutoDraw(false);
      }
    }
    psychoJS.experiment.addData('hlt_poststim.stopped', globalClock.getTime());
    // the Routine "hlt_poststim" was not non-slip safe, so reset the non-slip timer
    routineTimer.reset();
    
    // Routines running outside a loop should always advance the datafile row
    if (currentLoop === psychoJS.experiment) {
      psychoJS.experiment.nextEntry(snapshot);
    }
    return Scheduler.Event.NEXT;
  }
}

function hlt_responseRoutineBegin(snapshot) {
  return async function () {
    TrialHandler.fromSnapshot(snapshot); // ensure that .thisN vals are up to date
    
    //--- Prepare to start Routine 'hlt_response' ---
    t = 0;
    frameN = -1;
    continueRoutine = true; // until we're told otherwise
    hlt_responseClock.reset();
    routineTimer.reset();
    hlt_responseMaxDurationReached = false;
    // update component parameters for each repeat
    slider_4.reset()
    psychoJS.experiment.addData('hlt_response.started', globalClock.getTime());
    hlt_responseMaxDuration = null
    // keep track of which components have finished
    hlt_responseComponents = [];
    hlt_responseComponents.push(slider_4);
    
    for (const thisComponent of hlt_responseComponents)
      if ('status' in thisComponent)
        thisComponent.status = PsychoJS.Status.NOT_STARTED;
    return Scheduler.Event.NEXT;
  }
}

function hlt_responseRoutineEachFrame() {
  return async function () {
    //--- Loop for each frame of Routine 'hlt_response' ---
    // get current time
    t = hlt_responseClock.getTime();
    frameN = frameN + 1;// number of completed frames (so 0 is the first frame)
    // update/draw components on each frame
    
    // *slider_4* updates
    if (t >= 0.0 && slider_4.status === PsychoJS.Status.NOT_STARTED) {
      // keep track of start time/frame for later
      slider_4.tStart = t;  // (not accounting for frame time here)
      slider_4.frameNStart = frameN;  // exact frame index
      
      slider_4.setAutoDraw(true);
    }
    
    
    // Check slider_4 for response to end Routine
    if (slider_4.getRating() !== undefined && slider_4.status === PsychoJS.Status.STARTED) {
      continueRoutine = false; }
    // check for quit (typically the Esc key)
    if (psychoJS.experiment.experimentEnded || psychoJS.eventManager.getKeys({keyList:['escape']}).length > 0) {
      return quitPsychoJS('The [Escape] key was pressed. Goodbye!', false);
    }
    
    // check if the Routine should terminate
    if (!continueRoutine) {  // a component has requested a forced-end of Routine
      return Scheduler.Event.NEXT;
    }
    
    continueRoutine = false;  // reverts to True if at least one component still running
    for (const thisComponent of hlt_responseComponents)
      if ('status' in thisComponent && thisComponent.status !== PsychoJS.Status.FINISHED) {
        continueRoutine = true;
        break;
      }
    
    // refresh the screen if continuing
    if (continueRoutine) {
      return Scheduler.Event.FLIP_REPEAT;
    } else {
      return Scheduler.Event.NEXT;
    }
  };
}

function hlt_responseRoutineEnd(snapshot) {
  return async function () {
    //--- Ending Routine 'hlt_response' ---
    for (const thisComponent of hlt_responseComponents) {
      if (typeof thisComponent.setAutoDraw === 'function') {
        thisComponent.setAutoDraw(false);
      }
    }
    psychoJS.experiment.addData('hlt_response.stopped', globalClock.getTime());
    psychoJS.experiment.addData('slider_4.response', slider_4.getRating());
    psychoJS.experiment.addData('slider_4.rt', slider_4.getRT());
    // the Routine "hlt_response" was not non-slip safe, so reset the non-slip timer
    routineTimer.reset();
    
    // Routines running outside a loop should always advance the datafile row
    if (currentLoop === psychoJS.experiment) {
      psychoJS.experiment.nextEntry(snapshot);
    }
    return Scheduler.Event.NEXT;
  }
}

function let_welcomeRoutineBegin(snapshot) {
  return async function () {
    TrialHandler.fromSnapshot(snapshot); // ensure that .thisN vals are up to date
    
    //--- Prepare to start Routine 'let_welcome' ---
    t = 0;
    frameN = -1;
    continueRoutine = true; // until we're told otherwise
    let_welcomeClock.reset();
    routineTimer.reset();
    let_welcomeMaxDurationReached = false;
    // update component parameters for each repeat
    // setup some python lists for storing info about the mouse_3
    // current position of the mouse:
    mouse_3.x = [];
    mouse_3.y = [];
    mouse_3.leftButton = [];
    mouse_3.midButton = [];
    mouse_3.rightButton = [];
    mouse_3.time = [];
    gotValidClick = false; // until a click is received
    psychoJS.experiment.addData('let_welcome.started', globalClock.getTime());
    let_welcomeMaxDuration = null
    // keep track of which components have finished
    let_welcomeComponents = [];
    let_welcomeComponents.push(text_6);
    let_welcomeComponents.push(mouse_3);
    
    for (const thisComponent of let_welcomeComponents)
      if ('status' in thisComponent)
        thisComponent.status = PsychoJS.Status.NOT_STARTED;
    return Scheduler.Event.NEXT;
  }
}

function let_welcomeRoutineEachFrame() {
  return async function () {
    //--- Loop for each frame of Routine 'let_welcome' ---
    // get current time
    t = let_welcomeClock.getTime();
    frameN = frameN + 1;// number of completed frames (so 0 is the first frame)
    // update/draw components on each frame
    
    // *text_6* updates
    if (t >= 0.0 && text_6.status === PsychoJS.Status.NOT_STARTED) {
      // keep track of start time/frame for later
      text_6.tStart = t;  // (not accounting for frame time here)
      text_6.frameNStart = frameN;  // exact frame index
      
      text_6.setAutoDraw(true);
    }
    
    // *mouse_3* updates
    if (t >= 0.0 && mouse_3.status === PsychoJS.Status.NOT_STARTED) {
      // keep track of start time/frame for later
      mouse_3.tStart = t;  // (not accounting for frame time here)
      mouse_3.frameNStart = frameN;  // exact frame index
      
      mouse_3.status = PsychoJS.Status.STARTED;
      mouse_3.mouseClock.reset();
      prevButtonState = mouse_3.getPressed();  // if button is down already this ISN'T a new click
      }
    if (mouse_3.status === PsychoJS.Status.STARTED) {  // only update if started and not finished!
      _mouseButtons = mouse_3.getPressed();
      if (!_mouseButtons.every( (e,i,) => (e == prevButtonState[i]) )) { // button state changed?
        prevButtonState = _mouseButtons;
        if (_mouseButtons.reduce( (e, acc) => (e+acc) ) > 0) { // state changed to a new click
          _mouseXYs = mouse_3.getPos();
          mouse_3.x.push(_mouseXYs[0]);
          mouse_3.y.push(_mouseXYs[1]);
          mouse_3.leftButton.push(_mouseButtons[0]);
          mouse_3.midButton.push(_mouseButtons[1]);
          mouse_3.rightButton.push(_mouseButtons[2]);
          mouse_3.time.push(mouse_3.mouseClock.getTime());
          // end routine on response
          continueRoutine = false;
        }
      }
    }
    // check for quit (typically the Esc key)
    if (psychoJS.experiment.experimentEnded || psychoJS.eventManager.getKeys({keyList:['escape']}).length > 0) {
      return quitPsychoJS('The [Escape] key was pressed. Goodbye!', false);
    }
    
    // check if the Routine should terminate
    if (!continueRoutine) {  // a component has requested a forced-end of Routine
      return Scheduler.Event.NEXT;
    }
    
    continueRoutine = false;  // reverts to True if at least one component still running
    for (const thisComponent of let_welcomeComponents)
      if ('status' in thisComponent && thisComponent.status !== PsychoJS.Status.FINISHED) {
        continueRoutine = true;
        break;
      }
    
    // refresh the screen if continuing
    if (continueRoutine) {
      return Scheduler.Event.FLIP_REPEAT;
    } else {
      return Scheduler.Event.NEXT;
    }
  };
}

function let_welcomeRoutineEnd(snapshot) {
  return async function () {
    //--- Ending Routine 'let_welcome' ---
    for (const thisComponent of let_welcomeComponents) {
      if (typeof thisComponent.setAutoDraw === 'function') {
        thisComponent.setAutoDraw(false);
      }
    }
    psychoJS.experiment.addData('let_welcome.stopped', globalClock.getTime());
    // store data for psychoJS.experiment (ExperimentHandler)
    psychoJS.experiment.addData('mouse_3.x', mouse_3.x);
    psychoJS.experiment.addData('mouse_3.y', mouse_3.y);
    psychoJS.experiment.addData('mouse_3.leftButton', mouse_3.leftButton);
    psychoJS.experiment.addData('mouse_3.midButton', mouse_3.midButton);
    psychoJS.experiment.addData('mouse_3.rightButton', mouse_3.rightButton);
    psychoJS.experiment.addData('mouse_3.time', mouse_3.time);
    
    // the Routine "let_welcome" was not non-slip safe, so reset the non-slip timer
    routineTimer.reset();
    
    // Routines running outside a loop should always advance the datafile row
    if (currentLoop === psychoJS.experiment) {
      psychoJS.experiment.nextEntry(snapshot);
    }
    return Scheduler.Event.NEXT;
  }
}

function let_prestimRoutineBegin(snapshot) {
  return async function () {
    TrialHandler.fromSnapshot(snapshot); // ensure that .thisN vals are up to date
    
    //--- Prepare to start Routine 'let_prestim' ---
    t = 0;
    frameN = -1;
    continueRoutine = true; // until we're told otherwise
    let_prestimClock.reset();
    routineTimer.reset();
    let_prestimMaxDurationReached = false;
    // update component parameters for each repeat
    psychoJS.experiment.addData('let_prestim.started', globalClock.getTime());
    let_prestimMaxDuration = null
    // keep track of which components have finished
    let_prestimComponents = [];
    let_prestimComponents.push(black_screen_6);
    let_prestimComponents.push(cross_10);
    
    for (const thisComponent of let_prestimComponents)
      if ('status' in thisComponent)
        thisComponent.status = PsychoJS.Status.NOT_STARTED;
    return Scheduler.Event.NEXT;
  }
}

function let_prestimRoutineEachFrame() {
  return async function () {
    //--- Loop for each frame of Routine 'let_prestim' ---
    // get current time
    t = let_prestimClock.getTime();
    frameN = frameN + 1;// number of completed frames (so 0 is the first frame)
    // update/draw components on each frame
    
    // *black_screen_6* updates
    if (t >= 0.0 && black_screen_6.status === PsychoJS.Status.NOT_STARTED) {
      // keep track of start time/frame for later
      black_screen_6.tStart = t;  // (not accounting for frame time here)
      black_screen_6.frameNStart = frameN;  // exact frame index
      
      black_screen_6.setAutoDraw(true);
    }
    
    frameRemains = 0.0 + let_prestim_duration - psychoJS.window.monitorFramePeriod * 0.75;// most of one frame period left
    if (black_screen_6.status === PsychoJS.Status.STARTED && t >= frameRemains) {
      black_screen_6.setAutoDraw(false);
    }
    
    
    // *cross_10* updates
    if (t >= 0.0 && cross_10.status === PsychoJS.Status.NOT_STARTED) {
      // keep track of start time/frame for later
      cross_10.tStart = t;  // (not accounting for frame time here)
      cross_10.frameNStart = frameN;  // exact frame index
      
      cross_10.setAutoDraw(true);
    }
    
    frameRemains = 0.0 + let_prestim_duration - psychoJS.window.monitorFramePeriod * 0.75;// most of one frame period left
    if (cross_10.status === PsychoJS.Status.STARTED && t >= frameRemains) {
      cross_10.setAutoDraw(false);
    }
    
    // check for quit (typically the Esc key)
    if (psychoJS.experiment.experimentEnded || psychoJS.eventManager.getKeys({keyList:['escape']}).length > 0) {
      return quitPsychoJS('The [Escape] key was pressed. Goodbye!', false);
    }
    
    // check if the Routine should terminate
    if (!continueRoutine) {  // a component has requested a forced-end of Routine
      return Scheduler.Event.NEXT;
    }
    
    continueRoutine = false;  // reverts to True if at least one component still running
    for (const thisComponent of let_prestimComponents)
      if ('status' in thisComponent && thisComponent.status !== PsychoJS.Status.FINISHED) {
        continueRoutine = true;
        break;
      }
    
    // refresh the screen if continuing
    if (continueRoutine) {
      return Scheduler.Event.FLIP_REPEAT;
    } else {
      return Scheduler.Event.NEXT;
    }
  };
}

function let_prestimRoutineEnd(snapshot) {
  return async function () {
    //--- Ending Routine 'let_prestim' ---
    for (const thisComponent of let_prestimComponents) {
      if (typeof thisComponent.setAutoDraw === 'function') {
        thisComponent.setAutoDraw(false);
      }
    }
    psychoJS.experiment.addData('let_prestim.stopped', globalClock.getTime());
    // the Routine "let_prestim" was not non-slip safe, so reset the non-slip timer
    routineTimer.reset();
    
    // Routines running outside a loop should always advance the datafile row
    if (currentLoop === psychoJS.experiment) {
      psychoJS.experiment.nextEntry(snapshot);
    }
    return Scheduler.Event.NEXT;
  }
}

function let_stimRoutineBegin(snapshot) {
  return async function () {
    TrialHandler.fromSnapshot(snapshot); // ensure that .thisN vals are up to date
    
    //--- Prepare to start Routine 'let_stim' ---
    t = 0;
    frameN = -1;
    continueRoutine = true; // until we're told otherwise
    let_stimClock.reset();
    routineTimer.reset();
    let_stimMaxDurationReached = false;
    // update component parameters for each repeat
    let_sound.setValue(sound_path);
    let_sound.secs=let_stim_duration;
    let_sound.setVolume(1.0);
    psychoJS.experiment.addData('let_stim.started', globalClock.getTime());
    let_stimMaxDuration = null
    // keep track of which components have finished
    let_stimComponents = [];
    let_stimComponents.push(let_sound);
    let_stimComponents.push(black_screen_7);
    let_stimComponents.push(cross_11);
    
    for (const thisComponent of let_stimComponents)
      if ('status' in thisComponent)
        thisComponent.status = PsychoJS.Status.NOT_STARTED;
    return Scheduler.Event.NEXT;
  }
}

function let_stimRoutineEachFrame() {
  return async function () {
    //--- Loop for each frame of Routine 'let_stim' ---
    // get current time
    t = let_stimClock.getTime();
    frameN = frameN + 1;// number of completed frames (so 0 is the first frame)
    // update/draw components on each frame
    // start/stop let_sound
    if (t >= 0.0 && let_sound.status === PsychoJS.Status.NOT_STARTED) {
      // keep track of start time/frame for later
      let_sound.tStart = t;  // (not accounting for frame time here)
      let_sound.frameNStart = frameN;  // exact frame index
      
      psychoJS.window.callOnFlip(function(){ let_sound.play(); });  // screen flip
      let_sound.status = PsychoJS.Status.STARTED;
    }
    frameRemains = 0.0 + let_stim_duration - psychoJS.window.monitorFramePeriod * 0.75;// most of one frame period left
    if (let_sound.status === PsychoJS.Status.STARTED && t >= frameRemains) {
      if (t >= let_sound.tStart + 0.5) {
        let_sound.stop();  // stop the sound (if longer than duration)
        let_sound.status = PsychoJS.Status.FINISHED;
      }
    }
    
    // *black_screen_7* updates
    if (t >= 0.0 && black_screen_7.status === PsychoJS.Status.NOT_STARTED) {
      // keep track of start time/frame for later
      black_screen_7.tStart = t;  // (not accounting for frame time here)
      black_screen_7.frameNStart = frameN;  // exact frame index
      
      black_screen_7.setAutoDraw(true);
    }
    
    frameRemains = 0.0 + let_stim_duration - psychoJS.window.monitorFramePeriod * 0.75;// most of one frame period left
    if (black_screen_7.status === PsychoJS.Status.STARTED && t >= frameRemains) {
      black_screen_7.setAutoDraw(false);
    }
    
    
    // *cross_11* updates
    if (t >= 0.0 && cross_11.status === PsychoJS.Status.NOT_STARTED) {
      // keep track of start time/frame for later
      cross_11.tStart = t;  // (not accounting for frame time here)
      cross_11.frameNStart = frameN;  // exact frame index
      
      cross_11.setAutoDraw(true);
    }
    
    frameRemains = 0.0 + let_stim_duration - psychoJS.window.monitorFramePeriod * 0.75;// most of one frame period left
    if (cross_11.status === PsychoJS.Status.STARTED && t >= frameRemains) {
      cross_11.setAutoDraw(false);
    }
    
    // check for quit (typically the Esc key)
    if (psychoJS.experiment.experimentEnded || psychoJS.eventManager.getKeys({keyList:['escape']}).length > 0) {
      return quitPsychoJS('The [Escape] key was pressed. Goodbye!', false);
    }
    
    // check if the Routine should terminate
    if (!continueRoutine) {  // a component has requested a forced-end of Routine
      return Scheduler.Event.NEXT;
    }
    
    continueRoutine = false;  // reverts to True if at least one component still running
    for (const thisComponent of let_stimComponents)
      if ('status' in thisComponent && thisComponent.status !== PsychoJS.Status.FINISHED) {
        continueRoutine = true;
        break;
      }
    
    // refresh the screen if continuing
    if (continueRoutine) {
      return Scheduler.Event.FLIP_REPEAT;
    } else {
      return Scheduler.Event.NEXT;
    }
  };
}

function let_stimRoutineEnd(snapshot) {
  return async function () {
    //--- Ending Routine 'let_stim' ---
    for (const thisComponent of let_stimComponents) {
      if (typeof thisComponent.setAutoDraw === 'function') {
        thisComponent.setAutoDraw(false);
      }
    }
    psychoJS.experiment.addData('let_stim.stopped', globalClock.getTime());
    let_sound.stop();  // ensure sound has stopped at end of Routine
    // the Routine "let_stim" was not non-slip safe, so reset the non-slip timer
    routineTimer.reset();
    
    // Routines running outside a loop should always advance the datafile row
    if (currentLoop === psychoJS.experiment) {
      psychoJS.experiment.nextEntry(snapshot);
    }
    return Scheduler.Event.NEXT;
  }
}

function let_poststimRoutineBegin(snapshot) {
  return async function () {
    TrialHandler.fromSnapshot(snapshot); // ensure that .thisN vals are up to date
    
    //--- Prepare to start Routine 'let_poststim' ---
    t = 0;
    frameN = -1;
    continueRoutine = true; // until we're told otherwise
    let_poststimClock.reset();
    routineTimer.reset();
    let_poststimMaxDurationReached = false;
    // update component parameters for each repeat
    psychoJS.experiment.addData('let_poststim.started', globalClock.getTime());
    let_poststimMaxDuration = null
    // keep track of which components have finished
    let_poststimComponents = [];
    let_poststimComponents.push(black_screen_8);
    let_poststimComponents.push(cross_12);
    
    for (const thisComponent of let_poststimComponents)
      if ('status' in thisComponent)
        thisComponent.status = PsychoJS.Status.NOT_STARTED;
    return Scheduler.Event.NEXT;
  }
}

function let_poststimRoutineEachFrame() {
  return async function () {
    //--- Loop for each frame of Routine 'let_poststim' ---
    // get current time
    t = let_poststimClock.getTime();
    frameN = frameN + 1;// number of completed frames (so 0 is the first frame)
    // update/draw components on each frame
    
    // *black_screen_8* updates
    if (t >= 0.0 && black_screen_8.status === PsychoJS.Status.NOT_STARTED) {
      // keep track of start time/frame for later
      black_screen_8.tStart = t;  // (not accounting for frame time here)
      black_screen_8.frameNStart = frameN;  // exact frame index
      
      black_screen_8.setAutoDraw(true);
    }
    
    frameRemains = 0.0 + let_poststim_duration - psychoJS.window.monitorFramePeriod * 0.75;// most of one frame period left
    if (black_screen_8.status === PsychoJS.Status.STARTED && t >= frameRemains) {
      black_screen_8.setAutoDraw(false);
    }
    
    
    // *cross_12* updates
    if (t >= 0.0 && cross_12.status === PsychoJS.Status.NOT_STARTED) {
      // keep track of start time/frame for later
      cross_12.tStart = t;  // (not accounting for frame time here)
      cross_12.frameNStart = frameN;  // exact frame index
      
      cross_12.setAutoDraw(true);
    }
    
    frameRemains = 0.0 + let_poststim_duration - psychoJS.window.monitorFramePeriod * 0.75;// most of one frame period left
    if (cross_12.status === PsychoJS.Status.STARTED && t >= frameRemains) {
      cross_12.setAutoDraw(false);
    }
    
    // check for quit (typically the Esc key)
    if (psychoJS.experiment.experimentEnded || psychoJS.eventManager.getKeys({keyList:['escape']}).length > 0) {
      return quitPsychoJS('The [Escape] key was pressed. Goodbye!', false);
    }
    
    // check if the Routine should terminate
    if (!continueRoutine) {  // a component has requested a forced-end of Routine
      return Scheduler.Event.NEXT;
    }
    
    continueRoutine = false;  // reverts to True if at least one component still running
    for (const thisComponent of let_poststimComponents)
      if ('status' in thisComponent && thisComponent.status !== PsychoJS.Status.FINISHED) {
        continueRoutine = true;
        break;
      }
    
    // refresh the screen if continuing
    if (continueRoutine) {
      return Scheduler.Event.FLIP_REPEAT;
    } else {
      return Scheduler.Event.NEXT;
    }
  };
}

function let_poststimRoutineEnd(snapshot) {
  return async function () {
    //--- Ending Routine 'let_poststim' ---
    for (const thisComponent of let_poststimComponents) {
      if (typeof thisComponent.setAutoDraw === 'function') {
        thisComponent.setAutoDraw(false);
      }
    }
    psychoJS.experiment.addData('let_poststim.stopped', globalClock.getTime());
    // the Routine "let_poststim" was not non-slip safe, so reset the non-slip timer
    routineTimer.reset();
    
    // Routines running outside a loop should always advance the datafile row
    if (currentLoop === psychoJS.experiment) {
      psychoJS.experiment.nextEntry(snapshot);
    }
    return Scheduler.Event.NEXT;
  }
}

function let_responseRoutineBegin(snapshot) {
  return async function () {
    TrialHandler.fromSnapshot(snapshot); // ensure that .thisN vals are up to date
    
    //--- Prepare to start Routine 'let_response' ---
    t = 0;
    frameN = -1;
    continueRoutine = true; // until we're told otherwise
    let_responseClock.reset();
    routineTimer.reset();
    let_responseMaxDurationReached = false;
    // update component parameters for each repeat
    slider_5.reset()
    slider_6.reset()
    slider_7.reset()
    psychoJS.experiment.addData('let_response.started', globalClock.getTime());
    let_responseMaxDuration = null
    // keep track of which components have finished
    let_responseComponents = [];
    let_responseComponents.push(slider_5);
    let_responseComponents.push(slider_6);
    let_responseComponents.push(slider_7);
    
    for (const thisComponent of let_responseComponents)
      if ('status' in thisComponent)
        thisComponent.status = PsychoJS.Status.NOT_STARTED;
    return Scheduler.Event.NEXT;
  }
}

function let_responseRoutineEachFrame() {
  return async function () {
    //--- Loop for each frame of Routine 'let_response' ---
    // get current time
    t = let_responseClock.getTime();
    frameN = frameN + 1;// number of completed frames (so 0 is the first frame)
    // update/draw components on each frame
    
    // *slider_5* updates
    if (t >= 0.0 && slider_5.status === PsychoJS.Status.NOT_STARTED) {
      // keep track of start time/frame for later
      slider_5.tStart = t;  // (not accounting for frame time here)
      slider_5.frameNStart = frameN;  // exact frame index
      
      slider_5.setAutoDraw(true);
    }
    
    
    // Check slider_5 for response to end Routine
    if (slider_5.getRating() !== undefined && slider_5.status === PsychoJS.Status.STARTED) {
      continueRoutine = false; }
    
    // *slider_6* updates
    if (t >= 0.0 && slider_6.status === PsychoJS.Status.NOT_STARTED) {
      // keep track of start time/frame for later
      slider_6.tStart = t;  // (not accounting for frame time here)
      slider_6.frameNStart = frameN;  // exact frame index
      
      slider_6.setAutoDraw(true);
    }
    
    
    // Check slider_6 for response to end Routine
    if (slider_6.getRating() !== undefined && slider_6.status === PsychoJS.Status.STARTED) {
      continueRoutine = false; }
    
    // *slider_7* updates
    if (t >= 0.0 && slider_7.status === PsychoJS.Status.NOT_STARTED) {
      // keep track of start time/frame for later
      slider_7.tStart = t;  // (not accounting for frame time here)
      slider_7.frameNStart = frameN;  // exact frame index
      
      slider_7.setAutoDraw(true);
    }
    
    
    // Check slider_7 for response to end Routine
    if (slider_7.getRating() !== undefined && slider_7.status === PsychoJS.Status.STARTED) {
      continueRoutine = false; }
    // check for quit (typically the Esc key)
    if (psychoJS.experiment.experimentEnded || psychoJS.eventManager.getKeys({keyList:['escape']}).length > 0) {
      return quitPsychoJS('The [Escape] key was pressed. Goodbye!', false);
    }
    
    // check if the Routine should terminate
    if (!continueRoutine) {  // a component has requested a forced-end of Routine
      return Scheduler.Event.NEXT;
    }
    
    continueRoutine = false;  // reverts to True if at least one component still running
    for (const thisComponent of let_responseComponents)
      if ('status' in thisComponent && thisComponent.status !== PsychoJS.Status.FINISHED) {
        continueRoutine = true;
        break;
      }
    
    // refresh the screen if continuing
    if (continueRoutine) {
      return Scheduler.Event.FLIP_REPEAT;
    } else {
      return Scheduler.Event.NEXT;
    }
  };
}

function let_responseRoutineEnd(snapshot) {
  return async function () {
    //--- Ending Routine 'let_response' ---
    for (const thisComponent of let_responseComponents) {
      if (typeof thisComponent.setAutoDraw === 'function') {
        thisComponent.setAutoDraw(false);
      }
    }
    psychoJS.experiment.addData('let_response.stopped', globalClock.getTime());
    psychoJS.experiment.addData('slider_5.response', slider_5.getRating());
    psychoJS.experiment.addData('slider_5.rt', slider_5.getRT());
    psychoJS.experiment.addData('slider_6.response', slider_6.getRating());
    psychoJS.experiment.addData('slider_6.rt', slider_6.getRT());
    psychoJS.experiment.addData('slider_7.response', slider_7.getRating());
    psychoJS.experiment.addData('slider_7.rt', slider_7.getRT());
    // the Routine "let_response" was not non-slip safe, so reset the non-slip timer
    routineTimer.reset();
    
    // Routines running outside a loop should always advance the datafile row
    if (currentLoop === psychoJS.experiment) {
      psychoJS.experiment.nextEntry(snapshot);
    }
    return Scheduler.Event.NEXT;
  }
}

function ast_welcomeRoutineBegin(snapshot) {
  return async function () {
    TrialHandler.fromSnapshot(snapshot); // ensure that .thisN vals are up to date
    
    //--- Prepare to start Routine 'ast_welcome' ---
    t = 0;
    frameN = -1;
    continueRoutine = true; // until we're told otherwise
    ast_welcomeClock.reset();
    routineTimer.reset();
    ast_welcomeMaxDurationReached = false;
    // update component parameters for each repeat
    // setup some python lists for storing info about the mouse_4
    // current position of the mouse:
    mouse_4.x = [];
    mouse_4.y = [];
    mouse_4.leftButton = [];
    mouse_4.midButton = [];
    mouse_4.rightButton = [];
    mouse_4.time = [];
    gotValidClick = false; // until a click is received
    psychoJS.experiment.addData('ast_welcome.started', globalClock.getTime());
    ast_welcomeMaxDuration = null
    // keep track of which components have finished
    ast_welcomeComponents = [];
    ast_welcomeComponents.push(text_7);
    ast_welcomeComponents.push(mouse_4);
    
    for (const thisComponent of ast_welcomeComponents)
      if ('status' in thisComponent)
        thisComponent.status = PsychoJS.Status.NOT_STARTED;
    return Scheduler.Event.NEXT;
  }
}

function ast_welcomeRoutineEachFrame() {
  return async function () {
    //--- Loop for each frame of Routine 'ast_welcome' ---
    // get current time
    t = ast_welcomeClock.getTime();
    frameN = frameN + 1;// number of completed frames (so 0 is the first frame)
    // update/draw components on each frame
    
    // *text_7* updates
    if (t >= 0.0 && text_7.status === PsychoJS.Status.NOT_STARTED) {
      // keep track of start time/frame for later
      text_7.tStart = t;  // (not accounting for frame time here)
      text_7.frameNStart = frameN;  // exact frame index
      
      text_7.setAutoDraw(true);
    }
    
    // *mouse_4* updates
    if (t >= 0.0 && mouse_4.status === PsychoJS.Status.NOT_STARTED) {
      // keep track of start time/frame for later
      mouse_4.tStart = t;  // (not accounting for frame time here)
      mouse_4.frameNStart = frameN;  // exact frame index
      
      mouse_4.status = PsychoJS.Status.STARTED;
      mouse_4.mouseClock.reset();
      prevButtonState = mouse_4.getPressed();  // if button is down already this ISN'T a new click
      }
    if (mouse_4.status === PsychoJS.Status.STARTED) {  // only update if started and not finished!
      _mouseButtons = mouse_4.getPressed();
      if (!_mouseButtons.every( (e,i,) => (e == prevButtonState[i]) )) { // button state changed?
        prevButtonState = _mouseButtons;
        if (_mouseButtons.reduce( (e, acc) => (e+acc) ) > 0) { // state changed to a new click
          _mouseXYs = mouse_4.getPos();
          mouse_4.x.push(_mouseXYs[0]);
          mouse_4.y.push(_mouseXYs[1]);
          mouse_4.leftButton.push(_mouseButtons[0]);
          mouse_4.midButton.push(_mouseButtons[1]);
          mouse_4.rightButton.push(_mouseButtons[2]);
          mouse_4.time.push(mouse_4.mouseClock.getTime());
          // end routine on response
          continueRoutine = false;
        }
      }
    }
    // check for quit (typically the Esc key)
    if (psychoJS.experiment.experimentEnded || psychoJS.eventManager.getKeys({keyList:['escape']}).length > 0) {
      return quitPsychoJS('The [Escape] key was pressed. Goodbye!', false);
    }
    
    // check if the Routine should terminate
    if (!continueRoutine) {  // a component has requested a forced-end of Routine
      return Scheduler.Event.NEXT;
    }
    
    continueRoutine = false;  // reverts to True if at least one component still running
    for (const thisComponent of ast_welcomeComponents)
      if ('status' in thisComponent && thisComponent.status !== PsychoJS.Status.FINISHED) {
        continueRoutine = true;
        break;
      }
    
    // refresh the screen if continuing
    if (continueRoutine) {
      return Scheduler.Event.FLIP_REPEAT;
    } else {
      return Scheduler.Event.NEXT;
    }
  };
}

function ast_welcomeRoutineEnd(snapshot) {
  return async function () {
    //--- Ending Routine 'ast_welcome' ---
    for (const thisComponent of ast_welcomeComponents) {
      if (typeof thisComponent.setAutoDraw === 'function') {
        thisComponent.setAutoDraw(false);
      }
    }
    psychoJS.experiment.addData('ast_welcome.stopped', globalClock.getTime());
    // store data for psychoJS.experiment (ExperimentHandler)
    psychoJS.experiment.addData('mouse_4.x', mouse_4.x);
    psychoJS.experiment.addData('mouse_4.y', mouse_4.y);
    psychoJS.experiment.addData('mouse_4.leftButton', mouse_4.leftButton);
    psychoJS.experiment.addData('mouse_4.midButton', mouse_4.midButton);
    psychoJS.experiment.addData('mouse_4.rightButton', mouse_4.rightButton);
    psychoJS.experiment.addData('mouse_4.time', mouse_4.time);
    
    // the Routine "ast_welcome" was not non-slip safe, so reset the non-slip timer
    routineTimer.reset();
    
    // Routines running outside a loop should always advance the datafile row
    if (currentLoop === psychoJS.experiment) {
      psychoJS.experiment.nextEntry(snapshot);
    }
    return Scheduler.Event.NEXT;
  }
}

function ast_prestimRoutineBegin(snapshot) {
  return async function () {
    TrialHandler.fromSnapshot(snapshot); // ensure that .thisN vals are up to date
    
    //--- Prepare to start Routine 'ast_prestim' ---
    t = 0;
    frameN = -1;
    continueRoutine = true; // until we're told otherwise
    ast_prestimClock.reset();
    routineTimer.reset();
    ast_prestimMaxDurationReached = false;
    // update component parameters for each repeat
    psychoJS.experiment.addData('ast_prestim.started', globalClock.getTime());
    ast_prestimMaxDuration = null
    // keep track of which components have finished
    ast_prestimComponents = [];
    ast_prestimComponents.push(black_screen_9);
    ast_prestimComponents.push(cross_13);
    
    for (const thisComponent of ast_prestimComponents)
      if ('status' in thisComponent)
        thisComponent.status = PsychoJS.Status.NOT_STARTED;
    return Scheduler.Event.NEXT;
  }
}

function ast_prestimRoutineEachFrame() {
  return async function () {
    //--- Loop for each frame of Routine 'ast_prestim' ---
    // get current time
    t = ast_prestimClock.getTime();
    frameN = frameN + 1;// number of completed frames (so 0 is the first frame)
    // update/draw components on each frame
    
    // *black_screen_9* updates
    if (t >= 0.0 && black_screen_9.status === PsychoJS.Status.NOT_STARTED) {
      // keep track of start time/frame for later
      black_screen_9.tStart = t;  // (not accounting for frame time here)
      black_screen_9.frameNStart = frameN;  // exact frame index
      
      black_screen_9.setAutoDraw(true);
    }
    
    frameRemains = 0.0 + ast_prestim_duration - psychoJS.window.monitorFramePeriod * 0.75;// most of one frame period left
    if (black_screen_9.status === PsychoJS.Status.STARTED && t >= frameRemains) {
      black_screen_9.setAutoDraw(false);
    }
    
    
    // *cross_13* updates
    if (t >= 0.0 && cross_13.status === PsychoJS.Status.NOT_STARTED) {
      // keep track of start time/frame for later
      cross_13.tStart = t;  // (not accounting for frame time here)
      cross_13.frameNStart = frameN;  // exact frame index
      
      cross_13.setAutoDraw(true);
    }
    
    frameRemains = 0.0 + ast_prestim_duration - psychoJS.window.monitorFramePeriod * 0.75;// most of one frame period left
    if (cross_13.status === PsychoJS.Status.STARTED && t >= frameRemains) {
      cross_13.setAutoDraw(false);
    }
    
    // check for quit (typically the Esc key)
    if (psychoJS.experiment.experimentEnded || psychoJS.eventManager.getKeys({keyList:['escape']}).length > 0) {
      return quitPsychoJS('The [Escape] key was pressed. Goodbye!', false);
    }
    
    // check if the Routine should terminate
    if (!continueRoutine) {  // a component has requested a forced-end of Routine
      return Scheduler.Event.NEXT;
    }
    
    continueRoutine = false;  // reverts to True if at least one component still running
    for (const thisComponent of ast_prestimComponents)
      if ('status' in thisComponent && thisComponent.status !== PsychoJS.Status.FINISHED) {
        continueRoutine = true;
        break;
      }
    
    // refresh the screen if continuing
    if (continueRoutine) {
      return Scheduler.Event.FLIP_REPEAT;
    } else {
      return Scheduler.Event.NEXT;
    }
  };
}

function ast_prestimRoutineEnd(snapshot) {
  return async function () {
    //--- Ending Routine 'ast_prestim' ---
    for (const thisComponent of ast_prestimComponents) {
      if (typeof thisComponent.setAutoDraw === 'function') {
        thisComponent.setAutoDraw(false);
      }
    }
    psychoJS.experiment.addData('ast_prestim.stopped', globalClock.getTime());
    // the Routine "ast_prestim" was not non-slip safe, so reset the non-slip timer
    routineTimer.reset();
    
    // Routines running outside a loop should always advance the datafile row
    if (currentLoop === psychoJS.experiment) {
      psychoJS.experiment.nextEntry(snapshot);
    }
    return Scheduler.Event.NEXT;
  }
}

function stimRoutineBegin(snapshot) {
  return async function () {
    TrialHandler.fromSnapshot(snapshot); // ensure that .thisN vals are up to date
    
    //--- Prepare to start Routine 'stim' ---
    t = 0;
    frameN = -1;
    continueRoutine = true; // until we're told otherwise
    stimClock.reset();
    routineTimer.reset();
    stimMaxDurationReached = false;
    // update component parameters for each repeat
    current_sound.setValue(sound_path);
    current_sound.secs=ast_stim_duration;
    current_sound.setVolume(1.0);
    psychoJS.experiment.addData('stim.started', globalClock.getTime());
    stimMaxDuration = null
    // keep track of which components have finished
    stimComponents = [];
    stimComponents.push(current_sound);
    stimComponents.push(cross_14);
    
    for (const thisComponent of stimComponents)
      if ('status' in thisComponent)
        thisComponent.status = PsychoJS.Status.NOT_STARTED;
    return Scheduler.Event.NEXT;
  }
}

function stimRoutineEachFrame() {
  return async function () {
    //--- Loop for each frame of Routine 'stim' ---
    // get current time
    t = stimClock.getTime();
    frameN = frameN + 1;// number of completed frames (so 0 is the first frame)
    // update/draw components on each frame
    // start/stop current_sound
    if (t >= 0.0 && current_sound.status === PsychoJS.Status.NOT_STARTED) {
      // keep track of start time/frame for later
      current_sound.tStart = t;  // (not accounting for frame time here)
      current_sound.frameNStart = frameN;  // exact frame index
      
      psychoJS.window.callOnFlip(function(){ current_sound.play(); });  // screen flip
      current_sound.status = PsychoJS.Status.STARTED;
    }
    frameRemains = 0.0 + ast_stim_duration - psychoJS.window.monitorFramePeriod * 0.75;// most of one frame period left
    if (current_sound.status === PsychoJS.Status.STARTED && t >= frameRemains) {
      if (t >= current_sound.tStart + 0.5) {
        current_sound.stop();  // stop the sound (if longer than duration)
        current_sound.status = PsychoJS.Status.FINISHED;
      }
    }
    
    // *cross_14* updates
    if (t >= 0.0 && cross_14.status === PsychoJS.Status.NOT_STARTED) {
      // keep track of start time/frame for later
      cross_14.tStart = t;  // (not accounting for frame time here)
      cross_14.frameNStart = frameN;  // exact frame index
      
      cross_14.setAutoDraw(true);
    }
    
    frameRemains = 0.0 + ast_stim_duration - psychoJS.window.monitorFramePeriod * 0.75;// most of one frame period left
    if (cross_14.status === PsychoJS.Status.STARTED && t >= frameRemains) {
      cross_14.setAutoDraw(false);
    }
    
    // check for quit (typically the Esc key)
    if (psychoJS.experiment.experimentEnded || psychoJS.eventManager.getKeys({keyList:['escape']}).length > 0) {
      return quitPsychoJS('The [Escape] key was pressed. Goodbye!', false);
    }
    
    // check if the Routine should terminate
    if (!continueRoutine) {  // a component has requested a forced-end of Routine
      return Scheduler.Event.NEXT;
    }
    
    continueRoutine = false;  // reverts to True if at least one component still running
    for (const thisComponent of stimComponents)
      if ('status' in thisComponent && thisComponent.status !== PsychoJS.Status.FINISHED) {
        continueRoutine = true;
        break;
      }
    
    // refresh the screen if continuing
    if (continueRoutine) {
      return Scheduler.Event.FLIP_REPEAT;
    } else {
      return Scheduler.Event.NEXT;
    }
  };
}

function stimRoutineEnd(snapshot) {
  return async function () {
    //--- Ending Routine 'stim' ---
    for (const thisComponent of stimComponents) {
      if (typeof thisComponent.setAutoDraw === 'function') {
        thisComponent.setAutoDraw(false);
      }
    }
    psychoJS.experiment.addData('stim.stopped', globalClock.getTime());
    current_sound.stop();  // ensure sound has stopped at end of Routine
    // the Routine "stim" was not non-slip safe, so reset the non-slip timer
    routineTimer.reset();
    
    // Routines running outside a loop should always advance the datafile row
    if (currentLoop === psychoJS.experiment) {
      psychoJS.experiment.nextEntry(snapshot);
    }
    return Scheduler.Event.NEXT;
  }
}

function post_stimRoutineBegin(snapshot) {
  return async function () {
    TrialHandler.fromSnapshot(snapshot); // ensure that .thisN vals are up to date
    
    //--- Prepare to start Routine 'post_stim' ---
    t = 0;
    frameN = -1;
    continueRoutine = true; // until we're told otherwise
    post_stimClock.reset();
    routineTimer.reset();
    post_stimMaxDurationReached = false;
    // update component parameters for each repeat
    psychoJS.experiment.addData('post_stim.started', globalClock.getTime());
    post_stimMaxDuration = null
    // keep track of which components have finished
    post_stimComponents = [];
    post_stimComponents.push(black_screen_10);
    post_stimComponents.push(cross_15);
    
    for (const thisComponent of post_stimComponents)
      if ('status' in thisComponent)
        thisComponent.status = PsychoJS.Status.NOT_STARTED;
    return Scheduler.Event.NEXT;
  }
}

function post_stimRoutineEachFrame() {
  return async function () {
    //--- Loop for each frame of Routine 'post_stim' ---
    // get current time
    t = post_stimClock.getTime();
    frameN = frameN + 1;// number of completed frames (so 0 is the first frame)
    // update/draw components on each frame
    keys = event.getKeys()
    if 'escape' in keys and started_recording:
        s.sendall(b"stop\n")
        started_recording = False
    
    // *black_screen_10* updates
    if (t >= 0.0 && black_screen_10.status === PsychoJS.Status.NOT_STARTED) {
      // keep track of start time/frame for later
      black_screen_10.tStart = t;  // (not accounting for frame time here)
      black_screen_10.frameNStart = frameN;  // exact frame index
      
      black_screen_10.setAutoDraw(true);
    }
    
    frameRemains = 0.0 + ast_poststim_duration - psychoJS.window.monitorFramePeriod * 0.75;// most of one frame period left
    if (black_screen_10.status === PsychoJS.Status.STARTED && t >= frameRemains) {
      black_screen_10.setAutoDraw(false);
    }
    
    
    // *cross_15* updates
    if (t >= 0.0 && cross_15.status === PsychoJS.Status.NOT_STARTED) {
      // keep track of start time/frame for later
      cross_15.tStart = t;  // (not accounting for frame time here)
      cross_15.frameNStart = frameN;  // exact frame index
      
      cross_15.setAutoDraw(true);
    }
    
    frameRemains = 0.0 + ast_poststim_duration - psychoJS.window.monitorFramePeriod * 0.75;// most of one frame period left
    if (cross_15.status === PsychoJS.Status.STARTED && t >= frameRemains) {
      cross_15.setAutoDraw(false);
    }
    
    // check for quit (typically the Esc key)
    if (psychoJS.experiment.experimentEnded || psychoJS.eventManager.getKeys({keyList:['escape']}).length > 0) {
      return quitPsychoJS('The [Escape] key was pressed. Goodbye!', false);
    }
    
    // check if the Routine should terminate
    if (!continueRoutine) {  // a component has requested a forced-end of Routine
      return Scheduler.Event.NEXT;
    }
    
    continueRoutine = false;  // reverts to True if at least one component still running
    for (const thisComponent of post_stimComponents)
      if ('status' in thisComponent && thisComponent.status !== PsychoJS.Status.FINISHED) {
        continueRoutine = true;
        break;
      }
    
    // refresh the screen if continuing
    if (continueRoutine) {
      return Scheduler.Event.FLIP_REPEAT;
    } else {
      return Scheduler.Event.NEXT;
    }
  };
}

function post_stimRoutineEnd(snapshot) {
  return async function () {
    //--- Ending Routine 'post_stim' ---
    for (const thisComponent of post_stimComponents) {
      if (typeof thisComponent.setAutoDraw === 'function') {
        thisComponent.setAutoDraw(false);
      }
    }
    psychoJS.experiment.addData('post_stim.stopped', globalClock.getTime());
    // the Routine "post_stim" was not non-slip safe, so reset the non-slip timer
    routineTimer.reset();
    
    // Routines running outside a loop should always advance the datafile row
    if (currentLoop === psychoJS.experiment) {
      psychoJS.experiment.nextEntry(snapshot);
    }
    return Scheduler.Event.NEXT;
  }
}

function end_2RoutineBegin(snapshot) {
  return async function () {
    TrialHandler.fromSnapshot(snapshot); // ensure that .thisN vals are up to date
    
    //--- Prepare to start Routine 'end_2' ---
    t = 0;
    frameN = -1;
    continueRoutine = true; // until we're told otherwise
    end_2Clock.reset();
    routineTimer.reset();
    end_2MaxDurationReached = false;
    // update component parameters for each repeat
    // setup some python lists for storing info about the mouse_5
    // current position of the mouse:
    mouse_5.x = [];
    mouse_5.y = [];
    mouse_5.leftButton = [];
    mouse_5.midButton = [];
    mouse_5.rightButton = [];
    mouse_5.time = [];
    gotValidClick = false; // until a click is received
    psychoJS.experiment.addData('end_2.started', globalClock.getTime());
    end_2MaxDuration = null
    // keep track of which components have finished
    end_2Components = [];
    end_2Components.push(text_end);
    end_2Components.push(mouse_5);
    
    for (const thisComponent of end_2Components)
      if ('status' in thisComponent)
        thisComponent.status = PsychoJS.Status.NOT_STARTED;
    return Scheduler.Event.NEXT;
  }
}

function end_2RoutineEachFrame() {
  return async function () {
    //--- Loop for each frame of Routine 'end_2' ---
    // get current time
    t = end_2Clock.getTime();
    frameN = frameN + 1;// number of completed frames (so 0 is the first frame)
    // update/draw components on each frame
    
    // *text_end* updates
    if (t >= 0.0 && text_end.status === PsychoJS.Status.NOT_STARTED) {
      // keep track of start time/frame for later
      text_end.tStart = t;  // (not accounting for frame time here)
      text_end.frameNStart = frameN;  // exact frame index
      
      text_end.setAutoDraw(true);
    }
    
    // *mouse_5* updates
    if (t >= 0.0 && mouse_5.status === PsychoJS.Status.NOT_STARTED) {
      // keep track of start time/frame for later
      mouse_5.tStart = t;  // (not accounting for frame time here)
      mouse_5.frameNStart = frameN;  // exact frame index
      
      mouse_5.status = PsychoJS.Status.STARTED;
      mouse_5.mouseClock.reset();
      prevButtonState = mouse_5.getPressed();  // if button is down already this ISN'T a new click
      }
    if (mouse_5.status === PsychoJS.Status.STARTED) {  // only update if started and not finished!
      _mouseButtons = mouse_5.getPressed();
      if (!_mouseButtons.every( (e,i,) => (e == prevButtonState[i]) )) { // button state changed?
        prevButtonState = _mouseButtons;
        if (_mouseButtons.reduce( (e, acc) => (e+acc) ) > 0) { // state changed to a new click
          _mouseXYs = mouse_5.getPos();
          mouse_5.x.push(_mouseXYs[0]);
          mouse_5.y.push(_mouseXYs[1]);
          mouse_5.leftButton.push(_mouseButtons[0]);
          mouse_5.midButton.push(_mouseButtons[1]);
          mouse_5.rightButton.push(_mouseButtons[2]);
          mouse_5.time.push(mouse_5.mouseClock.getTime());
          // end routine on response
          continueRoutine = false;
        }
      }
    }
    // check for quit (typically the Esc key)
    if (psychoJS.experiment.experimentEnded || psychoJS.eventManager.getKeys({keyList:['escape']}).length > 0) {
      return quitPsychoJS('The [Escape] key was pressed. Goodbye!', false);
    }
    
    // check if the Routine should terminate
    if (!continueRoutine) {  // a component has requested a forced-end of Routine
      return Scheduler.Event.NEXT;
    }
    
    continueRoutine = false;  // reverts to True if at least one component still running
    for (const thisComponent of end_2Components)
      if ('status' in thisComponent && thisComponent.status !== PsychoJS.Status.FINISHED) {
        continueRoutine = true;
        break;
      }
    
    // refresh the screen if continuing
    if (continueRoutine) {
      return Scheduler.Event.FLIP_REPEAT;
    } else {
      return Scheduler.Event.NEXT;
    }
  };
}

function end_2RoutineEnd(snapshot) {
  return async function () {
    //--- Ending Routine 'end_2' ---
    for (const thisComponent of end_2Components) {
      if (typeof thisComponent.setAutoDraw === 'function') {
        thisComponent.setAutoDraw(false);
      }
    }
    psychoJS.experiment.addData('end_2.stopped', globalClock.getTime());
    // store data for psychoJS.experiment (ExperimentHandler)
    psychoJS.experiment.addData('mouse_5.x', mouse_5.x);
    psychoJS.experiment.addData('mouse_5.y', mouse_5.y);
    psychoJS.experiment.addData('mouse_5.leftButton', mouse_5.leftButton);
    psychoJS.experiment.addData('mouse_5.midButton', mouse_5.midButton);
    psychoJS.experiment.addData('mouse_5.rightButton', mouse_5.rightButton);
    psychoJS.experiment.addData('mouse_5.time', mouse_5.time);
    
    // the Routine "end_2" was not non-slip safe, so reset the non-slip timer
    routineTimer.reset();
    
    // Routines running outside a loop should always advance the datafile row
    if (currentLoop === psychoJS.experiment) {
      psychoJS.experiment.nextEntry(snapshot);
    }
    return Scheduler.Event.NEXT;
  }
}

function importConditions(currentLoop) {
  return async function () {
    psychoJS.importAttributes(currentLoop.getCurrentTrial());
    return Scheduler.Event.NEXT;
    };
}

async function quitPsychoJS(message, isCompleted) {
  // Check for and save orphaned data
  if (psychoJS.experiment.isEntryEmpty()) {
    psychoJS.experiment.nextEntry();
  }
  psychoJS.window.close();
  psychoJS.quit({message: message, isCompleted: isCompleted});
  
  return Scheduler.Event.QUIT;
}
