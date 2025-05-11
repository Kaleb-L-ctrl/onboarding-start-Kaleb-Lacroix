/*
 * Copyright (c) 2025 Kaleb Lacroix
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none

module SPI_perriferal (
    input wire SCLK,
    input wire nCS,
    input wire COPI,
    input wire clk,

    output reg [7:0] en_reg_out_7_0,
    output reg [7:0] en_reg_out_15_8,
    output reg [7:0] en_reg_pwm_7_0,
    output reg [7:0] en_reg_pwm_15_8,
    output reg [7:0] pwm_duty_cycle
);


    reg SCLKRISE;
    reg [1:0] SCLK_sync;
    reg [1:0] ncs_sync;
    reg [1:0] copi_sync;
    reg SCLK_buffer;
    reg [4:0] counter;
    reg [7:0] Madd; //message destination adress
    reg[7:0] Mdata; //message data
    reg [15,0] copi_message;

    always @(posedge clk) begin//on internal clock we sample through our buffers
        SCLK_buffer <= SCLK //avoids metastability with initital FF since we'll use SCLK_sync[0] for SCLKRISE so just one more layer here
        SCLK_sync <= {SCLK_sync[0], SCLK_buffer};
        copi_sync <= {cpoi_sync[0], copi};
        ncs_sync <= {ncs_sync[0], nCS};
        SCLKRISE <= (SCLK_sync[1] == 0)&&(SCLK_sync[0] == 1);
    end


    always @(SCLKRISE) begin//data valid take a sample and do the thing
        copi_message <= {copi_message[14:0], cpoi_sync[1]}//load in the new bit.
        counter += 1;

        if (counter == 15) begin
            counter <= 0;
            if (copi_message[15] == 1'b1) begin///we ignore read
                Madd<= copi_message[14:7];
                Mdata <= copi_message[7:0];
                case (Madd)// ***NTS this takes proroty over PWN enable
                    7'h00:en_reg_out_7_0  <= Mdata;
                    7'h01:en_reg_out_15_8 <= Mdata;
                    7'h02:en_reg_pwm_7_0  <= Mdata;
                    7'h03:en_reg_pwm_15_8 <= Mdata;
                    7'h04:pwm_duty_cycle  <= Mdata;
                    default:;//do nothing we are ignoring invalid adresses
                endcase
            end
        end
    end



    SCLKRISE = (SCLK_sync ==1)&&( prevSCLK == 0)
    prevSCLK <= SCLK_sync
  // All output pins must be assigned. If not used, assign to 0.

  // List all unused inputs to prevent warnings
  wire _unused = &{ena, clk, rst_n, 1'b0};

endmodule