function db = amp2db(amp)
% AMP2DB convert complex relative amplitude to decibels (dB)
%
% Input Params:
%  amp (MxN cplx) real or complex relative amplitudes
%
% Returns:
%  db  (MxN dbl) 20 log10(|amp|)
%
% db = AMP2DB(amp)
%
% COPYRIGHT ANSYS, Inc. ALL RIGHTS RESERVED.
db = 10*log10(real(amp.*conj(amp)));
end  % amp2db

