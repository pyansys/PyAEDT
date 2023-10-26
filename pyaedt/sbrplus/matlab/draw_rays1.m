function rndrCfg = draw_rays1(rayhdm,idxTrack,rndrCfg,newFig)
% DRAW_RAYS1 draws filtered ray bundle
%
% Renders rays has line segments, hit points, and/or triangular footprints,
% depending on rndrCfg settings.
%
% Input Params:
%  rayhdm (struct) ray bundle object returned by ld_sbrplushdm, must first be
%                  filtered using filter_rays1 or DRAW_RAYS1 throws an error
%
%  idxTrack (1xN int) index list of ray tracks to render, out-of-bounds indices
%                     ignored, DEFAULT = [] = render all ray tracks
%
%  rndrCfg (struct) rendering controls
%   .colorBy   (str) {'depth', 'Nrefl', 'Ntrans'} DEFAULT = 'depth'
%                    controls color for ray lines, hit points, and footprints,
%                    unless overridden by .colorByField
%
%   .colorByFld (str) {'Einc', 'Hrefl', 'Jtot', 'Mtrans', etc., or 'dist'}
%                     activates coloring ray footprints and hit points
%                     according to E or H field, in general any combination
%                     of {'E', 'H', 'J', 'M'} prefix and {'inc', 'refl',
%                     'trans', 'ir', 'tot'} suffix is supported, where 'ir'
%                     adds inc and refl fields and 'tot' further adds trans
%                     fields (if applicable), 'dist' colors by propagation
%                     distance from source, DEFAULT = empty = fall back to
%                     .colorBy property
%
%   .fldComp   (str) {'c', 'x', 'y', 'z', '-x', etc.}:
%                    composite, Fx, Fy, Fz, use '-' prefix for -Fx, etc.,
%                    which is useful for phase, DEFAULT = 'c'
%
%   .fldScale  (str) {'r', 'i', 'm', 'pw', 'd', 'ph'}:
%                    real, imag, mag, power, dB, phase, DEFAULT = dB
%
%   .ifreq     (int) frequency index when coloring ray footprints and hit
%                    points by field levels, DEFAULT = 1, 
%
%   .lineWidth (dbl) width of 1D rays, DEFAULT = 1, set to zero (0) to
%                    switch off render-by-line
%
%   .exitLen   (dbl) length of escaping rays [m], DEFAULT = 0 = do not render
%                    escaping rays
%
%   .ptSize    (dbl) size of hit points, DEFAULT = 0 = do not render source or
%                    hit points
%
%   .fpFaceClr (1x3 dbl) ray footprint face color {[R G B], MATLAB color
%               OR (str) string, 'none', 'flat'}, MATLAB color string can be
%                        a preset color or its short name (e.g., 'red', 'g')
%                        or a hex RGB color code string (e.g., '#ff0088'),
%                        set to 'flat' to follow .colorBy or .colorByFld,
%                        set to 'none' (DEFAULT) to not render ray footprint
%                        faces
%
%   .fpEdgeClr (1x3 dbl) ray footprint edge RGB color, see syntax for
%               OR (str) rndrCfg.fpFaceClr
%
%   .fpEdgeWidth   (dbl) ray footprint edge width, DEFAULT = 1
%
%   .fpOffset      (dbl) offset distance of rendered footprints along surface
%                        normal, DEFAULT = 0
%
%   .fpOffScale    (dbl) adjusts the footprint offset distance from .fpOffset
%                        according to the propagation distance of the footprint,
%                        allowing earlier or later footprints to be favored
%                        when they overlap, set to +1 for earliest (latest)
%                        footprints to be placed at 1 (2) x .fpOffset, set to
%                        -1 for opposite effect, set to 0 (DEFAULT) for all
%                        footprints to offset by .fpOffset (no offset scaling)
%
% Returns:
%  rndrCfg (struct) copy of input rndrCfg augmented with default values where
%                   applicable and with any unrecognized struct fields removed
%
%                      Summary of Input rndrCfg Struct Fields
% =============================================================================
% | Field Name  |    Type     |                Allowed Values                 |
% |             |             |    entry before semicolon is the default      |
% |=============+=============+===============================================+
% | colorBy     |     str     | depth; Nrefl, Ntrans                          |
% | colorByFld  |     str     | []; Einc, Hrefl, Jtot, Mtrans, etc., or dist  |
% | fldComp     |     str     | c; x, y, z, -x, -y, -z                        |
% | fldScale    |     str     | d; r, i, m, pw, ph                            |
% |-------------+-------------+-----------------------------------------------+
% | ifreq       |     int     | 1; [1,Nf]                                     |
% | lineWidth   |     dbl     | 1; 0 for no lines, [0,inf)                    |
% | exitLen     |     dbl     | 0 (no exit ray); [0,inf)                      |
% | ptSize      |     dbl     | 0 (no points); [0,inf)                        |
% |-------------+-------------+-----------------------------------------------+
% | fpFaceClr   | 1x3 dbl/str | none; flat, [0.5 0.5 1], red, g, #ff0088, etc.|
% | fpEdgeClr   | 1x3 dbl/str | none; flat, [0.5 0.5 1], red, g, #ff0088, etc.|
% | fpEdgeWidth |     dbl     | 1; [0,inf)                                    |
% | fpOffset    |     dbl     | 0; [0,inf)                                    |
% | fpOffScale  |     dbl     | 0; (-inf,inf)                                 |
% =============================================================================
%
% rndrCfg = DRAW_RAYS1(rayhdm[,idxTrack][,rndrCfg][,newFig])
%
% COPYRIGHT ANSYS, Inc. ALL RIGHTS RESERVED.

if ~exist('idxTrack','var') idxTrack = []; end

if ~exist('rndrCfg','var') rndrCfg = []; end

if ~isfield(rndrCfg,'colorBy') rndrCfg.colorBy = []; end
if isempty(rndrCfg.colorBy) rndrCfg.colorBy = 'depth'; end

if ~isfield(rndrCfg,'colorByFld') rndrCfg.colorByFld = []; end

if ~isfield(rndrCfg,'fldComp') rndrCfg.fldComp = []; end
if isempty(rndrCfg.fldComp) rndrCfg.fldComp = 'c'; end

if ~isfield(rndrCfg,'fldScale') rndrCfg.fldScale = []; end
if isempty(rndrCfg.fldScale) rndrCfg.fldScale = 'd'; end

if ~isfield(rndrCfg,'ifreq') rndrCfg.ifreq = []; end
if isempty(rndrCfg.ifreq) rndrCfg.ifreq = 1; end

if ~isfield(rndrCfg,'lineWidth') rndrCfg.lineWidth = []; end
if isempty(rndrCfg.lineWidth) rndrCfg.lineWidth = 1; end

if ~isfield(rndrCfg,'exitLen') rndrCfg.exitLen = []; end
if isempty(rndrCfg.exitLen) rndrCfg.exitLen = 0; end

if ~isfield(rndrCfg,'ptSize') rndrCfg.ptSize = []; end
if isempty(rndrCfg.ptSize) rndrCfg.ptSize = 0; end

if ~isfield(rndrCfg,'fpFaceClr') rndrCfg.fpFaceClr = []; end
if isempty(rndrCfg.fpFaceClr) rndrCfg.fpFaceClr = 'none'; end

if ~isfield(rndrCfg,'fpEdgeClr') rndrCfg.fpEdgeClr = []; end
if isempty(rndrCfg.fpEdgeClr) rndrCfg.fpEdgeClr = 'none'; end

if ~isfield(rndrCfg,'fpEdgeWidth') rndrCfg.fpEdgeWidth = []; end
if isempty(rndrCfg.fpEdgeWidth) rndrCfg.fpEdgeWidth = 1; end

if ~isfield(rndrCfg,'fpOffset') rndrCfg.fpOffset = []; end
if isempty(rndrCfg.fpOffset) rndrCfg.fpOffset = 0; end

if ~isfield(rndrCfg,'fpOffScale') rndrCfg.fpOffScale = []; end
if isempty(rndrCfg.fpOffScale) rndrCfg.fpOffScale = 0; end

if ~exist('newFig','var') newFig = []; end
if isempty(newFig) newFig = true; end

% validate and update rndrCfg fields
valid_flds = {'colorBy','colorByFld','fldComp','fldScale','ifreq', ...
              'lineWidth','ptSize','exitLen','fpFaceClr','fpEdgeClr', ...
              'fpEdgeWidth','fpOffset','fpOffScale'};
rndrCfg = validate_sfields(rndrCfg,valid_flds,'rndrCfg');

errIdBadInp = 'draw_rays1:badInput';  % use for any invocations of error()

% verify the ray bundle has been passed through filter_rays1()
bundle = rayhdm.hdm;
errMsg = ['Passed in ray bundle must be post-processed using ' ...
          'filter_rays1.m before rays can be rendered.'];
if ~isfield(bundle.hdmObj,'filter')
  error(errIdBadInp,errMsg);
end
if ~strcmp(bundle.hdmObj.filter,'filter_rays1')
  error(errIdBadInp,errMsg);
end

% convert rndrCfg settings into more convenient local booleans and values
colorByDepth = false;
colorByNrefl = false;
colorByNtrans = false;
switch rndrCfg.colorBy
 case 'depth'
  colorByDepth = true;
 case 'Nrefl'
  colorByNrefl = true;
 case 'Ntrans'
  colorByNtrans = true;
 otherwise
  error(errIdBadInp,'Invalid rndrCfg.colorBy value: %s',rndrCfg.colorBy);
end

drawLines = rndrCfg.lineWidth > 0;
drawPoints = rndrCfg.ptSize > 0;
drawEscape = rndrCfg.exitLen > 0;

% footprint offset
%
% In general, the footprint spatial offset along the surface normal is the base
% offset (rndrCfg.fpOffset) plus a scale factor times the difference between
% the cumulative path length distance of the footprint and either its minimum
% or maximum across all ray tracks. The scale factor is based on
% rndrCfg.fpOffScale.
%
% fpOffScale = +1:
%   offset = fpOffset*(1 + (dist - dist_min)/(dist_max - dist_min))
%          = fpOffset*(1 + (dist - dist_min)/dist_span)
%
% fpOffScale = -1:
%   offset = fpOffset*(1 + (dist_max - dist)/dist_span)
%
% We can generalize this to other values of .fpOffScale = scale.
%   scale >= 0: offset = fpOffset*(1 + scale*(dist - dist_min)/dist_span)
%   scale <  0: offset = fpOffset*(1 + scale*(dist - dist_max)/dist_span)
%
% This can be written as:
%   offset = offsetBase + offsetSlope*dist
%   scale >= 0:
%     offsetBase = fpOffset*(1 - scale*dist_min/dist_span);
%     offsetSlope = fpOffset*scale*dist/dist_span;
%
%   scale < 0:
%     offsetBase = fpOffset(1 - scale*dist_max/dist_span);
%     offsetSlope = fpOffset*scale/dist_span;

fpOffset = rndrCfg.fpOffset;
fpOffScale = rndrCfg.fpOffScale;
distMin = bundle.hdmObj.min_fp_cumulative_dist;
distMax = bundle.hdmObj.max_cumulative_dist;
distSpan = distMax - distMin;
offsetSlope = fpOffset*fpOffScale/distSpan;
if fpOffScale >= 0
  offsetBase = fpOffset*(1 - fpOffScale*distMin/distSpan);
else
  offsetBase = fpOffset*(1 - fpOffScale*distMax/distSpan);
end

% determine local booleans and values for footprint rendering

  %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
  function [drawIt fixedClr] = parse_color(clrParamName)
  % parse color spec from input
  %
  % Input Params:
  %  clrParamName (1x3 dbl) {[R G B], MATLAB color string, 'flat', 'none'},
  %                OR (str) color string can be a preset color or its short
  %                         name (e.g., 'red', 'g') or a hex RGB color string
  %
  % Returns:
  %  drawIt (lgc) true if clrParamName recognized and ~= 'none',
  %               false if clrParamName == 'none' or empty
  %
  %  fixedClr (1x3 dbl) RGB color, empty if clrParamName == 'same'
  drawIt = false;
  fixedClr = [];

  errMsg = ['Invalid ' clrParamName ' value, must be ' ...
            '{empty ([]),''none'',''same'', or [R G B]}'];
  paramVal = eval(clrParamName);

  if ischar(paramVal)
    switch paramVal
     case 'none'
      drawIt = false;
     case 'flat'
      drawIt = true;
     otherwise
      try
        fixedClr = validatecolor(paramVal);
        drawIt = true;
      catch me
        error(errIdBadInp,errMsg);
      end
    end
  
  else
    % paramVal not a char array, likely would have tripped up earlier switch
    % statement. If it's [R G B] numeric, we'll discover that here.
    try
      fixedClr = validatecolor(paramVal);
      drawIt = true;
    catch me
      error(errIdBadInp,errMsg);
    end
  end
  end  % parse_color
  %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

[drawFptFaces fptFixedFaceClr] = parse_color('rndrCfg.fpFaceClr');
[drawFptEdges fptFixedEdgeClr] = parse_color('rndrCfg.fpEdgeClr');

drawFpts = drawFptFaces || drawFptEdges;

% determine local booleans and values for color-by-field rendering
%
% init them first
doFldClr = false;
ifreq = 0;

doEFld = false;
doHFld = false;
doJCur = false;
doMCur = false;
doDist = false;

doIncFld = false;
doReflFld = false;
doTransFld = false;
transFldSign = 1.;

doCompositeFld = false;
doXFld = false;
doYFld = false;
doZFld = false;
fldCompSign = 1.;

doRealFld = false;
doImagFld = false;
doMagFld = false;
doPwrFld = false;
doDbFld = false;
doPhaseFld = false;

% parse rndrCfg.colorByFld, .fldComp, .fldScale, .ifreq
if ~isempty(rndrCfg.colorByFld)
  if ~ischar(rndrCfg.colorByFld) || (length(rndrCfg.colorByFld) < 4)
    error(errIdBadInp,...
          ['Invalid rndrCfg.colorByFld value, must either be empty or ' ...
           'a char array of length >= 4']);
  end

  cbfPrefix = rndrCfg.colorByFld(1);
  cbfSuffix = rndrCfg.colorByFld(2:end);

  if strcmp(lower(rndrCfg.colorByFld),'dist')
    doDist = true;
    cbfPrefix = '#';
    cbfSuffix = '#';
  end

  switch lower(cbfPrefix)
   case 'e'
    doEFld = true;

   case 'h'
    doHFld = true;

   case 'j'
    doJCur = true;

   case 'm'
    doMCur = true;

   case '#'
    % do nothing this is for colorByFld == 'dist'

   otherwise
    error(errIdBadInp,...
          ['Invalid rndrCfg.colorByFld value, first character must be ' ...
           '{''E'',''H'',''J'',''M''}']);
  end

  switch lower(cbfSuffix)
   case 'inc'
    doIncFld = true;

   case 'refl'
    doReflFld = true;

   case 'trans'
    doTransFld = true;

   case {'ir','increfl'}
    doIncFld = true;
    doReflFld = true;

   case {'tot','total'}
    doIncFld = true;
    doReflFld = true;
    doTransFld = true;

   case '#'
    % do nothing, this is for colorByFld == 'dist'

   otherwise
    error(errIdBadInp,...
          ['Invalid rndrCfg.colorByFld value, suffix after first ' ...
           'character must be {''inc'',''refl'',''trans'',''ir'',''tot''}']);
  end

  ifreq = rndrCfg.ifreq;
  if (length(ifreq) ~= 1) || ~isnumeric(ifreq)
    error(errIdBadInp,...
          'Invalid rndrCfg.ifreq value, must be a single integer index');
  end
  if ifreq ~= floor(ifreq)
    error(errIdBadInp,...
          'Invalid rndrCfg.ifreq value, must be an integer index');
  end
  % don't bounds check ifreq, clamp it (later) instead

  doFldClr = true;  % switch on color-by-field

  if doJCur || doMCur
    % account for flip in normal on transmission side when
    % using cross product to obtain equivalent currents
    transFldSign = -1.;
  end
end

if doFldClr
  if doDist
    rndrCfg.fldComp = 'x';  % hardwire, there will be special handling
  end
  switch lower(rndrCfg.fldComp)
   case {'c','comp','composite'}
    doCompositeFld = true;
   case 'x'
    doXFld = true;
   case 'y'
    doYFld = true;
   case 'z'
    doZFld = true;
   case '-x'
    doXFld = true;
    fldCompSign = -1;
   case '-y'
    doYFld = true;
    fldCompSign = -1;
   case '-z'
    doZFld = true;
    fldCompSign = -1;
   otherwise
    error(errIdBadInp,...
          ['Invalid rndrCfg.fldComp value, must be ' ...
           '{''c'',''x'',''y'',''z'',''-x'',''-y'',''-z'',empty}']);
  end

  if doDist
    rndrCfg.fldScale = 'r';  % hard-wire, there will be special handling
  end
  switch lower(rndrCfg.fldScale)
   case {'r','rl','real'}
    doRealFld = true;
   case {'i','im','imag'}
    doImagFld = true;
   case {'m','mag','magnitude','lin','linear'}
    doMagFld = true;
   case {'pw','pwr','power'}
    doPwrFld = true;
   case {'d','db','decibel'}
    doDbFld = true;
   case {'ph','phase','ang','angle'}
    doPhaseFld = true;
   otherwise
    error(errIdBadInp,...
          ['Invalid rndrCfg.fldScale value, must be ' ...
           '{''r'',''i'',''m'',''pw'',''db'',''ph'',empty}']);
  end

  if doCompositeFld && (doRealFld || doImagFld || doPhaseFld)
    error(errIdBadInp,...
          ['Cannot set field scale to ''r'' (real), ''i'' (imag), or ' ...
           '''ph'' (phase) when color-by-field component is ''c'' (composite)']);
  end
end

% define the ray color palette, an ordered list of colors
%
% When accessing rayClrs, the first color in the list should correspond
% to index = 0, so we need to make an index adjustment for MATLAB
% when accessing rayClrs by adding one to the index.
black = [0 0 0];
green = [0 1 0];
blue = [0 0 1];
cyan = [0 1 1];
magenta = [1 0 1];
red = [1 0 0];
orange = [0.85 0.325 0.098];  % used for UTD rays in some cases
rayClrs = [black;green;blue;cyan;magenta;red];
NrayClr = size(rayClrs,1);

Ntrack = length(bundle.hdmObj.ray_tracks);
Nf = length(bundle.hdmObj.frequency_list);
ifreq = min(max(1,ifreq),Nf);

if isempty(idxTrack)
  idxTrack = 1:Ntrack;
else
  idx0 = find((idxTrack > 0) & (idxTrack <= Ntrack));
  idxTrack = idxTrack(idx0);
  Ntrack = length(idxTrack);
end

  %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
  function recurse_track(rb)
  if ~rb.hdmObj.drawBranch
    % Entire branch switched off for rendering. Not rendering this bounce
    % or any of its descendants. No need to further descend the ray track
    % tree in search of bounces to draw --> early return to save effort.
    return;
  end

  rbParent = rb.hdmObj.parent;
  clr = [];
  fldClr = [];
  if (drawLines && isa(rbParent,'HdmObject'))
    %
    % RAY LINE SEGMENT RENDERING
    % Augment segsX, segsY, segsZ, segClrs to later draw ray line segments.
    %
    if (rbParent.hdmObj.drawBounce && rb.hdmObj.drawBounce)
      pt0 = rbParent.hdmObj.hit_pt;
      pt1 = rb.hdmObj.hit_pt;
      segsX = [segsX [pt0(1);pt1(1)]];
      segsY = [segsY [pt0(2);pt1(2)]];
      segsZ = [segsZ [pt0(3);pt1(3)]];
      clr = color_func(rb,false,false);  % cache to reuse for pts, footprints
      segClrs = [segClrs;clr];
    end
    if drawEscape
      if rb.hdmObj.drawTransEscape
        exit_pt = pt1 + rb.hdmObj.trans_escaped_ray*rndrCfg.exitLen;
        segsX = [segsX [pt1(1);exit_pt(1)]];
        segsY = [segsY [pt1(2);exit_pt(2)]];
        segsZ = [segsZ [pt1(3);exit_pt(3)]];
        segClrs = [segClrs;color_func(rb,true,false)];
      end

      if rb.hdmObj.drawReflEscape
        exit_pt = pt1 + rb.hdmObj.refl_escaped_ray*rndrCfg.exitLen;
        segsX = [segsX [pt1(1);exit_pt(1)]];
        segsY = [segsY [pt1(2);exit_pt(2)]];
        segsZ = [segsZ [pt1(3);exit_pt(3)]];
        segClrs = [segClrs;color_func(rb,false,true)];
      end
    end
  end

  if (drawPoints && rb.hdmObj.drawBounce)
    %
    % HIT POINT RENDERING
    % Augments pts and ptClrs to later render ray hit points.
    %
    pts = [pts;rb.hdmObj.hit_pt];
    if doFldClr
      fldClr = fld_clrdat(rb);
      ptClrs = [ptClrs;fldClr];
    else
      if isempty(clr)
        clr = color_func(rb,false,false);
      end
      ptClrs = [ptClrs;clr];
    end
  end

  if drawFpts && rb.hdmObj.drawBounce && ...
     (rb.hdmObj.bounce_type == SbrBounceType.Surface)
    %
    % RAY FOOTPRINT RENDERING
    % Augment fptVrts and fptClrs to later render ray footprint faces and/or
    % edges.
    %
    fptVrts0 = rb.hdmObj.footprint_vertices;
    if fpOffset
      offset = offsetBase + offsetSlope*rb.hdmObj.cumulative_dist;
      fptVrts0 = fptVrts0 + rb.hdmObj.surf_norm*offset;
    end
    fptVrts = [fptVrts;fptVrts0];

    if doFldClr
      if isempty(fldClr)
        fldClr = fld_clrdat(rb);  % Nfpt x 1, color-scale data
      end
      fptClrs = [fptClrs;fldClr];
    else
      if isempty(clr)
        clr = color_func(rb,false,false);  % Nfpt x 3, RGB colors
      end
      fptClrs = [fptClrs;clr];
    end
  end

  rbNext = rb.hdmObj.trans_bounce;
  if ~isempty(rbNext)
    depth = depth + 1;
    tDepth = tDepth + 1;
    recurse_track(rbNext);
    depth = depth - 1;
    tDepth = tDepth - 1;
  end

  rbNext = rb.hdmObj.refl_bounce;
  if ~isempty(rbNext)
    depth = depth + 1;
    isSurfBnc = (rb.hdmObj.bounce_type == SbrBounceType.Surface);
    if isSurfBnc
      rDepth = rDepth + 1;
    end
    recurse_track(rbNext);
    depth = depth - 1;
    if isSurfBnc
      rDepth = rDepth - 1;
    end
  end
  end  % recurse_track

  %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
  function clr = depth_color(rb,drawTransEscape,drawReflEscape)
  % return ray/bounce color RGB when coloring by tree depth of bounce
  %
  % Intended to by called via color_func function pointer, implements
  % its expected interface.
  if depth == 0
    clr = red;
    return;
  end
  if drawTransEscape || drawReflEscape
    % Escaping rays don't have their own bounce object, but we consider
    % their track depth to be one more than the depth of the bounce that
    % produces them: (depth + 1) + 1 = depth + 2
    clr = rayClrs(min(depth + 2,NrayClr),:);
  else
    % conceptually, rayClrs starts at index (i.e. depth) = 0, so adjust
    % for MATLAB indexing
    clr = rayClrs(min(depth + 1,NrayClr),:);
  end
  end  % depth_color

  %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
  function clr = Nrefl_color(rb,drawTransEscape,drawReflEscape)
  % return ray/bounce color RGB according to max refl depth among branches
  %
  % Intended to by called via color_func function pointer, implements
  % its expected interface.
  if depth == 0
    % draw source point as red, only occurs when rendering points
    clr = red;
    return;
  end
  if rb.hdmObj.bounce_type == SbrBounceType.UtdEdge
    % draw UTD diffraction point as orange
    clr = orange;
    return;
  end
  if drawTransEscape
    % for the 'branch' of an escaping transmission ray, the maximum
    % reflection depth is reflection depth of the bounce
    clr = rayClrs(min(rDepth + 1,NrayClr),:);
  else
    clr = rayClrs(min(rb.hdmObj.maxRDepth + 1,NrayClr),:);
  end
  end  % Nrefl_color

  %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
  function clr = Ntrans_color(rb,drawTransEscape,drawReflEscape)
  % return ray/bounce color RGB according to max trans depth among branches
  %
  % Intended to by called via color_func function pointer, implements
  % its expected interface.
  if depth == 0
    % draw source point as red, only occurs when rendering points
    clr = red;
    return;
  end  
  if rb.hdmObj.bounce_type == SbrBounceType.UtdEdge
    % draw UTD diffraction point as orange
    clr = orange;
    return;
  end
  if drawReflEscape
    % for the 'branch' of an escaping reflection ray, the maximum
    % transmission depth is the transmission depth of the bounce
    clr = rayClrs(min(tDepth + 1,NrayClr),:);
  else
    clr = rayClrs(min(rb.hdmObj.maxTDepth + 1,NrayClr),:);
  end
  end  % Nrefl_color

  %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
  function cdat = fld_clrdat(rb)
  % return a scalar color value (not RGB) based on fields at bounce
  cdat = nan;
  if (rb.hdmObj.bounce_type ~= SbrBounceType.Surface) && ~doDist
    % this can happen when fld_clrdat is called for source or UTD diffraction
    % point, return nan and deal with it later
    return;
  end
  vec_field_func(rb);  % gets E, H, J, or M, caches in bncFld external
  field_comp_func(); % gets Fx, Fy, Fz, -Fx, -Fy, -Fz, or |F|^2 
  cdat = field_clrdat_func();  % real(F), imag(F), |F|, etc.
  end  % fld_clrdat

  %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
  function efield(rb)
  % determine electric field vector at specified ray bounce and cache in bncFld
  % external
  %
  % Depending on rndrCfg.colorByField settings, computes/grabs Einc, Erefl,
  % +/- Etrans, Einc + Erefl, or Einc + Erefl +/- Etrans. The sign in front of
  % Etrans is negative when this function is called by mcur() to account for
  % the flipped face normal on the transmission sign when using the cross
  % product to generate equivalent magnetic current.
  %
  % Intended to be called via vec_field_func function pointer (or mcur()),
  % implements its expected interface.
  % Uses ifreq external to specify the frequency index to retrieve.
  bncFld = [0 0 0];  % external scope
  if doIncFld && rb.hdmObj.flags.HasIncField
    bncFld = rb.hdmObj.e_inc(ifreq,:);
  end

  if doReflFld && rb.hdmObj.flags.HasReflField
    bncFld = bncFld + rb.hdmObj.e_refl(ifreq,:);
  end

  if doTransFld && rb.hdmObj.flags.HasTransField
    % transFldSign = 1 when E-field is ultimately wanted.
    % transFldSign = -1 when equivalent M current is wanted from E-field
    %                   to account for flip in surface normal used in
    %                   cross product.
    bncFld = bncFld + rb.hdmObj.e_trans(ifreq,:)*transFldSign;
  end
  end  % get_efield

  %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
  function hfield(rb)
  % determine magnetic field vector at specified ray bounce and cache in bncFld
  % external
  %
  % See function interface doc for efield().
  bncFld = [0 0 0];  % external scope
  if doIncFld && rb.hdmObj.flags.HasIncField
    bncFld = rb.hdmObj.h_inc(ifreq,:);
  end

  if doReflFld && rb.hdmObj.flags.HasReflField
    bncFld = bncFld + rb.hdmObj.h_refl(ifreq,:);
  end

  if doTransFld && rb.hdmObj.flags.HasTransField
    % transFldSign = 1 when H-field is ultimately wanted.
    % transFldSign = -1 when equivalent J current is wanted from H-field
    %                   to account for flip in surface normal used in
    %                   cross product.
    bncFld = bncFld + rb.hdmObj.h_trans(ifreq,:)*transFldSign;
  end
  end  % get_hfield

  %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
  function jcur(rb)
  % determine vector equivalent electric current at specified ray bounce and
  % cache in bncFld external
  %
  % Intended to be called via vec_field_func function pointer and implements
  % its expected interface.
  % Uses ifreq external to specify the frequency index to retrieve.
  hfield(rb);
  bncFld = cross(rb.hdmObj.surf_norm,bncFld);  % n X H
  end  % jcur

  %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
  function mcur(rb)
  % determine vector equivalent magnetic current at specified ray bounce and
  % cache in bncFld external
  %
  % Intended to be called via vec_field_func function pointer and implements
  % its expected interface.
  % Uses ifreq external to specify the frequency index to retrieve.
  efield(rb);
  bncFld = cross(bncFld,rb.hdmObj.surf_norm);  % -n x E
  end  % mcur

  %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
  function cumulative_dist(rb)
  % determine cumulative path length at specified ray bounce and cache in
  % x-component of bncFld
  %
  % Intended to be called via vec_field_func function pointer and implements
  % its expected interface.
  bncFld = [rb.hdmObj.cumulative_dist 0 0];
  end  % cumulative_dist

  %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
  function field_component()
  % selects x, y, z, -x, -y, or -z component of cached bncFld external
  % (1x3 cmplx), storing the complex scalar back in bncFld
  %
  % Intended to be called via field_comp_func function pointer and implements
  % its expected interface.
  bncFld = bncFld(iFldComp)*fldCompSign;  % external scope
  end  % get_field_component

  %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
  function field_composite()
  % evaluates |bncFld|^2 and replaces result in bncFld external
  %
  % Intended to be called via field_comp_func function pointer and implements
  % its expected interface.
  bncFld = real(sum(bncFld.*conj(bncFld)));  % external scope
  end

  %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
  function cdat = field_real()
  % returns real part of bncFld scalar complex external
  %
  % Intended to be called via field_clrdat_func function pointer and implements
  % its expected interface.
  cdat = real(bncFld);
  end

  %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
  function cdat = field_imag()
  cdat = imag(bncFld);
  end

  %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
  function cdat = field_mag_from_component()
  % returns magnitude of bncFld scalar complex external
  %
  % Intended to be called via field_clrdat_func function pointer and implements
  % its expected interface. Makes sense when bncFld contains a complex scalar
  % component of a vector field (e.g., Ex, -Hz, etc.).
  cdat = abs(bncFld);
  end

  %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
  function cdat = field_mag_from_composite()
  % returns square root of bncFld real-number external
  %
  % Intended to be called via field_clrdat_func function pointer and implements
  % its expected interface. Makes sense when bncFld contains magnitude squared
  % of composite field (e.g., |Ex|^2 + |Ey|^2 + |Ez|^2).
  cdat = sqrt(bncFld);
  end

  %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
  function cdat = field_pwr_from_component()
  % returns magnitude squared of bncFld scalar complex external
  %
  % Intended to be called via field_clrdat_func function pointer and implements
  % its expected interface. Makes sense when bncFld contains a complex scalar
  % component of a vector field (e.g., Ex, -Hz, etc.).
  cdat = real(bncFld.*conj(bncFld));
  end

  %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
  function cdat = field_pwr_from_composite()
  % returns bncFld real-number external
  %
  % Intended to be called via field_clrdat_func function pointer and implements
  % its expected interface. Makes sense when bncFld already contains magnitude
  % squared of composite field (e.g., |Ex|^2 + |Ey|^2 + |Ez|^2).
  cdat = bncFld;
  end

  %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
  function cdat = field_db_from_component()
  % returns bncFld field-scale complex phasor as real number in dB
  %
  % Intended to be called via field_clrdat_func function pointer and implements
  % its expected interface. Makes sense when bncFld contains a complex scalar
  % component of a vector field (e.g., Ex, -Hz, etc.).
  cdat = amp2db(bncFld);
  end

  %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
  function cdat = field_db_from_composite()
  % returns bncFld linear power-scale value in dB
  %
  % Intended to be called via field_clrdat_func function pointer and implements
  % its expected interface. Makes sense when bncFld contains magnitude squared
  % squared of composite field (e.g., |Ex|^2 + |Ey|^2 + |Ez|^2).
  cdat = pwr2db(bncFld);
  end

  %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
  function cdat = field_phase()
  % returns polar angle in radians of bncFld scalar complex external
  %
  % Intended to be called via field_clrdat_func function pointer and implements
  % its expected interface. Makes sense when bncFld contains a complex scalar
  % component of a vector field (e.g., Ex, -Hz, etc.).
  cdat = angle(bncFld);
  end

  %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

hdmStruct.hit_pt = [];
hdmStruct.drawBounce = true;

% define and init vectors and matrices to be augmented by recurse_track()
% for rendering the rays as lines, points, and footprints
pts = [];     % Nx3 hit points
ptClrs = [];  % Nx3 hit point RGB colors or 1x3 hit point color data
segsX = [];   % 2xN X-values of ray track segments, one column per segment
segsY = [];   % 2xN Y-values ...
segsZ = [];   % 2xN Z-values ...
segClrs = []; % Nx3 RGB colors of ray track segments
fptVrts = []; % 3Nx3 footprint vertices, 3 rows per footprint
fptClrs = []; % Nx3 footprint RGB colors or Nx1 footprint color data
bncFld = [];  % temp var shared by functions called by fld_clrdat

% assign the color function that is called during ray track tree recursion
%
% Any function assigned here must implement the following interface:
% clr = color_func(rb,drawTransEscape,drawReflEscape)
%
% drawTransEscape and drawReflEscape cannot be both true at same time:
%   [drawTransEscape, drawReflEscape] = {[f,f], [t,f], or [f,t]}
%
% Input Params:
%   rb (HdmObject) ray bounce object
%   drawTransEscape (lgc) true if retrieving color for escaping ray on
%                         transmission side
%   drawReflEscape (lgc) true if retrieving color for escaping ray on
%                        reflection side
%
% Returns:
%  clr (1x3 dbl) [R G B] color
%
color_func = [];
if colorByDepth
  color_func = @depth_color;
elseif colorByNrefl
  color_func = @Nrefl_color;
elseif colorByNtrans
  color_func = @Ntrans_color;
else
  color_func = @depth_color;
end

% assign functions called by fld_clrdat() to set a color-scale value
% for ray footprints when coloring by field
vec_field_func = [];     % vec_field_func(ray_bounce_HdmObject)
field_comp_func = [];    % field_comp_func()
field_clrdat_func = [];  % cdat = field_clrdat_func()
iFldComp = 0;
if doFldClr
  if doEFld
    vec_field_func = @efield;
  elseif doHFld
    vec_field_func = @hfield;
  elseif doJCur
    vec_field_func = @jcur;
  elseif doMCur
    vec_field_func = @mcur;
  elseif doDist
    vec_field_func = @cumulative_dist;
  end

  if doCompositeFld
    field_comp_func = @field_composite;
  else
    field_comp_func = @field_component;
    if doXFld
      iFldComp = 1;
    elseif doYFld
      iFldComp = 2;
    elseif doZFld
      iFldComp = 3;
    end
  end

  if doRealFld
    field_clrdat_func = @field_real;

  elseif doImagFld
    field_clrdat_func = @field_imag;

  elseif doMagFld
    if doCompositeFld
      field_clrdat_func = @field_mag_from_composite;
    else
      field_clrdat_func = @field_mag_from_component;
    end

  elseif doPwrFld
    if doCompositeFld
      field_clrdat_func = @field_pwr_from_composite;
    else
      field_clrdat_func = @field_pwr_from_component;
    end

  elseif doDbFld
    if doCompositeFld
      field_clrdat_func = @field_db_from_composite;
    else
      field_clrdat_func = @field_db_from_component;
    end

  elseif doPhaseFld
    field_clrdat_func = @field_phase;

  end
end  % doFldClr

if newFig
  figure;
else
  hold on;
end
for itrack = idxTrack
  % Descend the ray-track tree, starting from the "source bounce", an
  % artificial bounce introduced by filter_rays1() to simplify post-proc code
  % logic. The first bounce is encoded as a originating from a REFLECTION
  % off the "source bounce", which is an entirely arbitrary and ad hoc
  % crow-barring into the existing ray-track framework. If ray track
  % is UTD, then filter_rays1() introduces an artificial bounce for the
  % UTD diffraction point, and it goes between the source bounce and the
  % first bounce.
  %
  % Init all depths to zero. They will be incremented and decremented
  % going up and down the track tree as applicable.
  rb0 = bundle.hdmObj.ray_tracks(itrack).hdmObj.source_bounce;
  depth = 0;  % composite bounce depth
  rDepth = 0; % reflection depth
  tDepth = 0; % transmission depth
  recurse_track(rb0);
end

% Init the color order list that determines the colors of anything rendered
% as a line:
% - ray track segments
% - outlines of ray footprints (drawn using plot3) when footprint faces are
%   not rendered (via patch)
clrOrder = [];

if drawLines
  plot3(segsX,segsY,segsZ,'LineWidth',rndrCfg.lineWidth);
  hold on;
  clrOrder = [clrOrder;segClrs];
end

if drawFpts
  % render ray footprints as faces and/or edges
  %
  % Build up face list as [1 2 3;4 5 6; ...],
  Nfpt = size(fptClrs,1);
  fptFaces = [1 2 3] + transpose(0:(Nfpt - 1))*3;

  % To support per-footprint coloring of faces and/or edges, set the color data
  % per vertex rather than per face. At this point,both fptFaces and fptClrs
  % have Nfpt rows, while fptVrts has 3 Nfpt rows. Replicate the data in fptClrs
  % to have 3 Nfpt rows.
  Nvrt = size(fptVrts,1);  % should be 3 Nfpt, but not checking
  if size(fptClrs,2) == 3
    fptClrs = reshape(fptClrs,1,3*Nfpt);  % [R1 R2 ... G1 G2 ... B1 B2 ...]
    fptClrs = repmat(fptClrs,3,1);
    fptClrs = reshape(fptClrs,Nvrt,3);
  else
    fptClrs = repmat(transpose(fptClrs),3,1);
    fptClrs = reshape(fptClrs,Nvrt,1);
  end

  hs = patch('Vertices',fptVrts,'Faces',fptFaces,'FaceVertexCData',fptClrs);
  if drawFptFaces
    if isempty(fptFixedFaceClr)
      set(hs,'FaceColor','flat');
    else
      set(hs,'FaceColor',fptFixedFaceClr);
    end
  else
    set(hs,'FaceColor','none');
  end

  if drawFptEdges
    set(hs,'LineWidth',rndrCfg.fpEdgeWidth);
    if isempty(fptFixedEdgeClr)
      set(hs,'EdgeColor','flat');
    else
      set(hs,'EdgeColor',fptFixedEdgeClr);
    end
  else
    set(hs,'EdgeColor','none');
  end
  hold on;
end

if ~isempty(clrOrder)
  % set colors of any plotted as lines
  set(gca,'colororder',clrOrder);
end

if drawPoints
  if size(ptClrs,2) == 1
    clrMax = max(ptClrs);
    idx = find(isnan(ptClrs));
    ptClrs(idx) = clrMax;
  end
  scatter3(pts(:,1),pts(:,2),pts(:,3),10*rndrCfg.ptSize^2,ptClrs,'filled');
  hold on;
end

hold off;

axis vis3d;
axis equal;

end  % draw_rays1
